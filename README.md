# Taller 3 ADSO - Tienda FastAPI

API REST de gestión de pedidos con FastAPI, PyMySQL y MySQL/MariaDB.

## Preparación

1. Cree un entorno virtual y actívelo.
2. Instale las dependencias:

   ```text
   python -m pip install -r requirements.txt
   ```

3. En Workbench o phpMyAdmin, ejecute primero `sql/01_esquema.sql` y luego `sql/02_datos_prueba.sql`.
4. Copie `.env.example` como `.env` y configure la cuenta de aplicación.
5. Inicie la API desde la raíz del proyecto:

   ```text
   fastapi dev app/main.py
   ```

6. Abra `http://127.0.0.1:8000/docs`.

No entregue el archivo `.env` ni el entorno virtual.
