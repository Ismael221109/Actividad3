from decimal import Decimal

from fastapi import APIRouter, HTTPException

from app.database import conectar
from app.schemas import PedidoActualizar, PedidoCrear


router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


@router.post("", status_code=201)
def crear(datos: PedidoCrear):
    # Una transacción atómica: pedido + detalle + descuento de stock.
    # SELECT FOR UPDATE bloquea las filas involucradas hasta finalizar.
    if len({item.producto_id for item in datos.items}) != len(datos.items):
        raise HTTPException(422, "No repita el mismo producto en un pedido")

    with conectar() as db:
        with db.cursor() as cur:
            cur.execute(
                "SELECT id FROM clientes WHERE id=%s",
                (datos.cliente_id,),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "Cliente no encontrado")

            # Bloqueo en orden estable para disminuir conflictos concurrentes.
            items = sorted(datos.items, key=lambda item: item.producto_id)
            detalles = []
            total = Decimal("0.00")

            for item in items:
                cur.execute(
                    "SELECT id,precio,stock FROM productos WHERE id=%s FOR UPDATE",
                    (item.producto_id,),
                )
                producto = cur.fetchone()
                if producto is None:
                    raise HTTPException(
                        404,
                        f"Producto {item.producto_id} no encontrado",
                    )
                if producto["stock"] < item.cantidad:
                    raise HTTPException(
                        409,
                        f"Stock insuficiente del producto {item.producto_id}",
                    )

                subtotal = producto["precio"] * item.cantidad
                total += subtotal
                detalles.append(
                    (
                        item.producto_id,
                        item.cantidad,
                        producto["precio"],
                        subtotal,
                    )
                )

            cur.execute(
                "INSERT INTO pedidos (cliente_id,total) VALUES (%s,%s)",
                (datos.cliente_id, total),
            )
            pedido_id = cur.lastrowid

            for producto_id, cantidad, precio, subtotal in detalles:
                cur.execute(
                    """
                    INSERT INTO detalle_pedidos
                        (pedido_id,producto_id,cantidad,precio_unitario,subtotal)
                    VALUES (%s,%s,%s,%s,%s)
                    """,
                    (pedido_id, producto_id, cantidad, precio, subtotal),
                )
                cur.execute(
                    "UPDATE productos SET stock=stock-%s WHERE id=%s",
                    (cantidad, producto_id),
                )

            return {
                "id": pedido_id,
                "cliente_id": datos.cliente_id,
                "estado": "confirmado",
                "total": str(total),
                "items": len(detalles),
            }


@router.get("")
def listar():
    with conectar() as db:
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.cliente_id, p.fecha, p.estado, p.total,
                       c.nombre AS cliente
                FROM pedidos p
                JOIN clientes c ON c.id=p.cliente_id
                ORDER BY p.id DESC
                """
            )
            return cur.fetchall()


@router.get("/estado/{estado}")
def listar_por_estado(estado: str):
    estados_permitidos = {"pendiente", "confirmado", "cancelado"}
    if estado not in estados_permitidos:
        raise HTTPException(422, "Estado no válido")

    with conectar() as db:
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.fecha, p.estado, p.total,
                       c.nombre AS cliente
                FROM pedidos p
                JOIN clientes c ON c.id=p.cliente_id
                WHERE p.estado=%s
                ORDER BY p.fecha DESC
                """,
                (estado,),
            )
            return cur.fetchall()


@router.get("/{pedido_id}")
def detalle(pedido_id: int):
    with conectar() as db:
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.fecha, p.estado, p.total,
                       c.nombre AS cliente
                FROM pedidos p
                JOIN clientes c ON c.id=p.cliente_id
                WHERE p.id=%s
                """,
                (pedido_id,),
            )
            pedido = cur.fetchone()
            if pedido is None:
                raise HTTPException(404, "Pedido no encontrado")

            cur.execute(
                """
                SELECT d.producto_id, pr.nombre AS producto, d.cantidad,
                       d.precio_unitario, d.subtotal
                FROM detalle_pedidos d
                JOIN productos pr ON pr.id=d.producto_id
                WHERE d.pedido_id=%s
                ORDER BY d.id
                """,
                (pedido_id,),
            )
            pedido["items"] = cur.fetchall()
            return pedido


@router.patch("/{pedido_id}")
def actualizar(pedido_id: int, datos: PedidoActualizar):
    cambios = datos.model_dump(exclude_unset=True)
    if not cambios:
        raise HTTPException(422, "Debe enviar al menos un campo")

    with conectar() as db:
        with db.cursor() as cur:
            cur.execute(
                "SELECT cliente_id, estado FROM pedidos WHERE id=%s FOR UPDATE",
                (pedido_id,),
            )
            pedido = cur.fetchone()
            if pedido is None:
                raise HTTPException(404, "Pedido no encontrado")

            if "cliente_id" in cambios:
                cur.execute(
                    "SELECT id FROM clientes WHERE id=%s",
                    (cambios["cliente_id"],),
                )
                if cur.fetchone() is None:
                    raise HTTPException(404, "Cliente no encontrado")

            estado_anterior = pedido["estado"]
            estado_nuevo = cambios.get("estado", estado_anterior)
            detalles = []

            if estado_anterior != estado_nuevo:
                cur.execute(
                    "SELECT producto_id, cantidad FROM detalle_pedidos "
                    "WHERE pedido_id=%s",
                    (pedido_id,),
                )
                detalles = cur.fetchall()

            if estado_anterior == "confirmado" and estado_nuevo == "cancelado":
                for detalle in detalles:
                    cur.execute(
                        "UPDATE productos SET stock=stock+%s WHERE id=%s",
                        (detalle["cantidad"], detalle["producto_id"]),
                    )

            if estado_anterior == "cancelado" and estado_nuevo == "confirmado":
                for detalle in sorted(detalles, key=lambda item: item["producto_id"]):
                    cur.execute(
                        "SELECT stock FROM productos WHERE id=%s FOR UPDATE",
                        (detalle["producto_id"],),
                    )
                    producto = cur.fetchone()
                    if producto is None:
                        raise HTTPException(404, "Producto del pedido no encontrado")
                    if producto["stock"] < detalle["cantidad"]:
                        raise HTTPException(
                            409,
                            "Stock insuficiente para confirmar el pedido",
                        )
                    cur.execute(
                        "UPDATE productos SET stock=stock-%s WHERE id=%s",
                        (detalle["cantidad"], detalle["producto_id"]),
                    )

            campos = []
            valores = []
            for campo, valor in cambios.items():
                campos.append(f"{campo}=%s")
                valores.append(valor)
            valores.append(pedido_id)
            cur.execute(
                f"UPDATE pedidos SET {', '.join(campos)} WHERE id=%s",
                tuple(valores),
            )
            cur.execute(
                "SELECT p.id,p.cliente_id,p.fecha,p.estado,p.total,c.nombre AS cliente "
                "FROM pedidos p JOIN clientes c ON c.id=p.cliente_id "
                "WHERE p.id=%s",
                (pedido_id,),
            )
            return cur.fetchone()


@router.delete("/{pedido_id}", status_code=204)
def eliminar(pedido_id: int):
    with conectar() as db:
        with db.cursor() as cur:
            cur.execute(
                "SELECT estado FROM pedidos WHERE id=%s FOR UPDATE",
                (pedido_id,),
            )
            pedido = cur.fetchone()
            if pedido is None:
                raise HTTPException(404, "Pedido no encontrado")

            cur.execute(
                "SELECT producto_id,cantidad FROM detalle_pedidos "
                "WHERE pedido_id=%s",
                (pedido_id,),
            )
            detalles = cur.fetchall()

            if pedido["estado"] != "cancelado":
                for detalle in detalles:
                    cur.execute(
                        "UPDATE productos SET stock=stock+%s WHERE id=%s",
                        (detalle["cantidad"], detalle["producto_id"]),
                    )

            cur.execute(
                "DELETE FROM detalle_pedidos WHERE pedido_id=%s",
                (pedido_id,),
            )
            cur.execute("DELETE FROM pedidos WHERE id=%s", (pedido_id,))


@router.patch("/{pedido_id}/estado")
def actualizar_estado(pedido_id: int, estado: str):
    estados_permitidos = {"pendiente", "confirmado", "cancelado"}
    if estado not in estados_permitidos:
        raise HTTPException(422, "Estado no válido")

    with conectar() as db:
        with db.cursor() as cur:
            cur.execute(
                "SELECT estado FROM pedidos WHERE id=%s FOR UPDATE",
                (pedido_id,),
            )
            pedido = cur.fetchone()
            if pedido is None:
                raise HTTPException(404, "Pedido no encontrado")
            cur.execute(
                "UPDATE pedidos SET estado=%s WHERE id=%s",
                (estado, pedido_id),
            )
            cur.execute(
                "SELECT * FROM pedidos WHERE id=%s",
                (pedido_id,),
            )
            return cur.fetchone()

