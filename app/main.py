from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import clientes, productos, pedidos


app = FastAPI(
    title="Taller 3 ADSO - Tienda",
    version="3.0",
    description="API relacional: clientes, productos, pedidos y detalles",
)
frontend = Path(__file__).resolve().parent / "frontend"

app.mount("/static", StaticFiles(directory=frontend), name="static")
app.include_router(clientes.router)
app.include_router(productos.router)
app.include_router(pedidos.router)


@app.get("/", tags=["Inicio"])
def inicio():
    return FileResponse(frontend / "index.html")
