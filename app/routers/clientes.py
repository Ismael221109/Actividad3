from fastapi import APIRouter, HTTPException
from pymysql.err import IntegrityError

from app.database import conectar
from app.schemas import ClienteActualizar, ClienteCrear, ClienteRespuesta


router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("/{cliente_id}/pedidos")
def pedidos_cliente(cliente_id: int):
    with conectar() as db:
        with db.cursor() as cur:
            cur.execute(
                "SELECT * FROM clientes WHERE id=%s",
                (cliente_id,),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "Cliente no encontrado")
            cur.execute(
                """
                SELECT p.id, p.fecha, p.estado, p.total
                FROM pedidos p
                WHERE p.cliente_id=%s
                ORDER BY p.fecha DESC
                """,
                (cliente_id,),
            )
            return cur.fetchall()


@router.get("", response_model=list[ClienteRespuesta])
def listar():
    with conectar() as db:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM clientes ORDER BY id")
            return cur.fetchall()


@router.get("/{cliente_id}", response_model=ClienteRespuesta)
def obtener(cliente_id: int):
    with conectar() as db:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM clientes WHERE id=%s", (cliente_id,))
            cliente = cur.fetchone()
            if cliente is None:
                raise HTTPException(404, "Cliente no encontrado")
            return cliente


@router.post("", response_model=ClienteRespuesta, status_code=201)
def crear(datos: ClienteCrear):
    try:
        with conectar() as db:
            with db.cursor() as cur:
                cur.execute(
                    "INSERT INTO clientes (nombre,correo) VALUES (%s,%s)",
                    (datos.nombre, str(datos.correo)),
                )
                nuevo_id = cur.lastrowid
                cur.execute("SELECT * FROM clientes WHERE id=%s", (nuevo_id,))
                return cur.fetchone()
    except IntegrityError as exc:
        raise HTTPException(409, "Correo ya registrado") from exc


@router.patch("/{cliente_id}", response_model=ClienteRespuesta)
def actualizar(cliente_id: int, datos: ClienteActualizar):
    cambios = datos.model_dump(exclude_unset=True)
    if not cambios:
        raise HTTPException(422, "Debe enviar al menos un campo")

    try:
        with conectar() as db:
            with db.cursor() as cur:
                cur.execute("SELECT * FROM clientes WHERE id=%s", (cliente_id,))
                cliente = cur.fetchone()
                if cliente is None:
                    raise HTTPException(404, "Cliente no encontrado")

                campos = []
                valores = []
                for campo, valor in cambios.items():
                    campos.append(f"{campo}=%s")
                    valores.append(str(valor) if campo == "correo" else valor)
                valores.append(cliente_id)
                cur.execute(
                    f"UPDATE clientes SET {', '.join(campos)} WHERE id=%s",
                    tuple(valores),
                )
                cur.execute("SELECT * FROM clientes WHERE id=%s", (cliente_id,))
                return cur.fetchone()
    except IntegrityError as exc:
        raise HTTPException(409, "Correo ya registrado") from exc


@router.delete("/{cliente_id}", status_code=204)
def eliminar(cliente_id: int):
    try:
        with conectar() as db:
            with db.cursor() as cur:
                cur.execute("DELETE FROM clientes WHERE id=%s", (cliente_id,))
                if cur.rowcount == 0:
                    raise HTTPException(404, "Cliente no encontrado")
    except IntegrityError as exc:
        raise HTTPException(
            409,
            "El cliente tiene pedidos y no puede eliminarse",
        ) from exc
