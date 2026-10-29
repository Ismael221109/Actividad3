from fastapi import APIRouter, HTTPException, Query

from app.database import conectar
from app.schemas import ProductoActualizar, ProductoCrear, ProductoRespuesta
from pymysql.err import IntegrityError


router = APIRouter(prefix="/productos", tags=["Productos"])


@router.get("/buscar/nombre")
def buscar_por_nombre(nombre: str = Query(min_length=1)):
    with conectar() as db:
        with db.cursor() as cur:
            cur.execute(
                "SELECT * FROM productos WHERE nombre LIKE %s ORDER BY nombre",
                (f"%{nombre}%",),
            )
            return cur.fetchall()


@router.get("", response_model=list[ProductoRespuesta])
def listar(
    buscar: str | None = None,
    pagina: int = Query(1, ge=1),
    limite: int = Query(10, ge=1, le=50),
):
    sql = "SELECT * FROM productos"
    params = []
    if buscar:
        sql += " WHERE nombre LIKE %s"
        params.append(f"%{buscar}%")
    sql += " ORDER BY id LIMIT %s OFFSET %s"
    params.extend([limite, (pagina - 1) * limite])
    with conectar() as db:
        with db.cursor() as cur:
            cur.execute(sql, tuple(params))
            return cur.fetchall()


@router.get("/{producto_id}", response_model=ProductoRespuesta)
def obtener(producto_id: int):
    with conectar() as db:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM productos WHERE id=%s", (producto_id,))
            producto = cur.fetchone()
            if producto is None:
                raise HTTPException(404, "Producto no encontrado")
            return producto


@router.post("", response_model=ProductoRespuesta, status_code=201)
def crear(datos: ProductoCrear):
    with conectar() as db:
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO productos (nombre,precio,stock) VALUES (%s,%s,%s)",
                (datos.nombre, datos.precio, datos.stock),
            )
            nuevo_id = cur.lastrowid
            cur.execute("SELECT * FROM productos WHERE id=%s", (nuevo_id,))
            return cur.fetchone()


@router.patch("/{producto_id}/stock", response_model=ProductoRespuesta)
def cambiar_stock(producto_id: int, stock: int = Query(ge=0)):
    with conectar() as db:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE productos SET stock=%s WHERE id=%s",
                (stock, producto_id),
            )
            if cur.rowcount == 0:
                raise HTTPException(404, "Producto no encontrado")
            cur.execute("SELECT * FROM productos WHERE id=%s", (producto_id,))
            return cur.fetchone()


@router.patch("/{producto_id}", response_model=ProductoRespuesta)
def actualizar(producto_id: int, datos: ProductoActualizar):
    cambios = datos.model_dump(exclude_unset=True)
    if not cambios:
        raise HTTPException(422, "Debe enviar al menos un campo")

    with conectar() as db:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM productos WHERE id=%s", (producto_id,))
            producto = cur.fetchone()
            if producto is None:
                raise HTTPException(404, "Producto no encontrado")

            campos = [f"{campo}=%s" for campo in cambios]
            valores = list(cambios.values()) + [producto_id]
            cur.execute(
                f"UPDATE productos SET {', '.join(campos)} WHERE id=%s",
                tuple(valores),
            )
            cur.execute("SELECT * FROM productos WHERE id=%s", (producto_id,))
            return cur.fetchone()


@router.delete("/{producto_id}", status_code=204)
def eliminar(producto_id: int):
    try:
        with conectar() as db:
            with db.cursor() as cur:
                cur.execute("DELETE FROM productos WHERE id=%s", (producto_id,))
                if cur.rowcount == 0:
                    raise HTTPException(404, "Producto no encontrado")
    except IntegrityError as exc:
        raise HTTPException(
            409,
            "El producto está asociado a pedidos y no puede eliminarse",
        ) from exc
