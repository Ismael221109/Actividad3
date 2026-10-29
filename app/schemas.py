from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class ClienteCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    correo: EmailStr


class ClienteRespuesta(ClienteCrear):
    id: int


class ProductoCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    precio: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    stock: int = Field(ge=0)


class ProductoRespuesta(ProductoCrear):
    id: int


class ClienteActualizar(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=100)
    correo: Optional[EmailStr] = None


class ProductoActualizar(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=100)
    precio: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    stock: Optional[int] = Field(default=None, ge=0)


class ItemPedido(BaseModel):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(gt=0)


class PedidoCrear(BaseModel):
    cliente_id: int = Field(gt=0)
    items: list[ItemPedido] = Field(min_length=1)


class PedidoActualizar(BaseModel):
    cliente_id: Optional[int] = Field(default=None, gt=0)
    estado: Optional[Literal["pendiente", "confirmado", "cancelado"]] = None
