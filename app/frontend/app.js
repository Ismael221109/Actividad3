const money = new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
});

const state = { clientes: [], productos: [], pedidos: [] };

function toast(message) {
    const element = document.getElementById("toast");
    element.textContent = message;
    element.classList.add("visible");
    setTimeout(() => element.classList.remove("visible"), 3000);
}

async function request(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.detail || "No se pudo completar la operación");
    }
    return data;
}

async function loadData() {
    try {
        const [clientes, productos, pedidos] = await Promise.all([
            request("/clientes"),
            request("/productos?limite=50"),
            request("/pedidos"),
        ]);
        state.clientes = clientes;
        state.productos = productos;
        state.pedidos = pedidos;
        render();
    } catch (error) {
        toast(error.message);
    }
}

function render() {
    document.getElementById("totalClientes").textContent = state.clientes.length;
    document.getElementById("totalProductos").textContent = state.productos.length;
    document.getElementById("totalPedidos").textContent = state.pedidos.length;

    document.getElementById("clientsTable").innerHTML = state.clientes.length
        ? state.clientes.map(cliente => `
            <tr>
                <td>${cliente.id}</td>
                <td>${escapeHtml(cliente.nombre)}</td>
                <td>${escapeHtml(cliente.correo)}</td>
                <td class="actions">
                    <button class="action-button" data-edit-client="${cliente.id}">Editar</button>
                    <button class="action-button delete" data-delete-client="${cliente.id}">Eliminar</button>
                </td>
            </tr>
        `).join("")
        : '<tr><td colspan="4">No hay clientes registrados</td></tr>';

    document.getElementById("productsTable").innerHTML = state.productos.length
        ? state.productos.map(producto => `
            <tr>
                <td>${producto.id}</td>
                <td>${escapeHtml(producto.nombre)}</td>
                <td>${money.format(producto.precio)}</td>
                <td class="${producto.stock < 5 ? "stock-low" : ""}">${producto.stock}</td>
                <td class="actions">
                    <button class="action-button" data-edit-product="${producto.id}">Editar</button>
                    <button class="action-button delete" data-delete-product="${producto.id}">Eliminar</button>
                </td>
            </tr>
        `).join("")
        : '<tr><td colspan="5">No hay productos registrados</td></tr>';

    document.getElementById("ordersTable").innerHTML = state.pedidos.length
        ? state.pedidos.map(pedido => `
            <tr>
                <td>#${pedido.id}</td>
                <td>${escapeHtml(pedido.cliente)}</td>
                <td>${formatDate(pedido.fecha)}</td>
                <td><span class="badge">${escapeHtml(pedido.estado)}</span></td>
                <td>${money.format(pedido.total)}</td>
                <td class="actions">
                    <button class="action-button" data-edit-order="${pedido.id}">Editar</button>
                    <button class="action-button delete" data-delete-order="${pedido.id}">Eliminar</button>
                </td>
            </tr>
        `).join("")
        : '<tr><td colspan="6">No hay pedidos registrados</td></tr>';

    document.getElementById("recentOrders").innerHTML = state.pedidos.slice(0, 4).length
        ? state.pedidos.slice(0, 4).map(pedido => `
            <div class="recent-item"><span>#${pedido.id} · ${escapeHtml(pedido.cliente)}</span><strong>${money.format(pedido.total)}</strong></div>
        `).join("")
        : '<p>No hay pedidos registrados.</p>';

    fillSelect("orderClient", state.clientes, "id", "nombre");
    fillSelect("orderProduct", state.productos, "id", "nombre");
}

function fillSelect(id, rows, valueKey, labelKey) {
    const select = document.getElementById(id);
    select.innerHTML = rows.map(row =>
        `<option value="${row[valueKey]}">${escapeHtml(row[labelKey])}</option>`
    ).join("");
}

function formatDate(value) {
    if (!value) return "-";
    return new Date(value).toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });
}

function escapeHtml(value) {
    const element = document.createElement("div");
    element.textContent = String(value ?? "");
    return element.innerHTML;
}

function showView(view) {
    document.querySelectorAll(".view").forEach(section => section.classList.remove("active"));
    document.getElementById(view).classList.add("active");
    document.querySelectorAll(".nav-item").forEach(item => item.classList.toggle("active", item.dataset.view === view));
    document.getElementById("pageTitle").textContent =
        view === "inicio" ? "Inicio" : view[0].toUpperCase() + view.slice(1);
    document.querySelector(".sidebar").classList.remove("open");
}

document.querySelectorAll(".nav-item").forEach(button => {
    button.addEventListener("click", () => showView(button.dataset.view));
});
document.querySelectorAll("[data-go]").forEach(button => {
    button.addEventListener("click", () => showView(button.dataset.go));
});
document.getElementById("menuButton").addEventListener("click", () => {
    document.querySelector(".sidebar").classList.toggle("open");
});

document.getElementById("openClientModal").addEventListener("click", () => {
    resetClientModal();
    document.getElementById("clientModal").showModal();
});
document.getElementById("openProductModal").addEventListener("click", () => {
    resetProductModal();
    document.getElementById("productModal").showModal();
});
document.getElementById("openOrderModal").addEventListener("click", () => {
    resetOrderModal();
    document.getElementById("orderModal").showModal();
});
document.querySelectorAll(".close-modal").forEach(button => button.addEventListener("click", () => button.closest("dialog").close()));

document.addEventListener("click", async event => {
    const editClient = event.target.closest("[data-edit-client]");
    const deleteClient = event.target.closest("[data-delete-client]");
    const editProduct = event.target.closest("[data-edit-product]");
    const deleteProduct = event.target.closest("[data-delete-product]");
    const editOrder = event.target.closest("[data-edit-order]");
    const deleteOrder = event.target.closest("[data-delete-order]");

    if (editClient) openClientEditor(Number(editClient.dataset.editClient));
    if (deleteClient && confirm("¿Eliminar este cliente?")) {
        await deleteRecord(`/clientes/${deleteClient.dataset.deleteClient}`, "Cliente eliminado");
    }
    if (editProduct) openProductEditor(Number(editProduct.dataset.editProduct));
    if (deleteProduct && confirm("¿Eliminar este producto?")) {
        await deleteRecord(`/productos/${deleteProduct.dataset.deleteProduct}`, "Producto eliminado");
    }
    if (editOrder) openOrderEditor(Number(editOrder.dataset.editOrder));
    if (deleteOrder && confirm("¿Eliminar este pedido y devolver su stock?")) {
        await deleteRecord(`/pedidos/${deleteOrder.dataset.deleteOrder}`, "Pedido eliminado y stock restaurado");
    }
});

function openClientEditor(id) {
    const cliente = state.clientes.find(item => item.id === id);
    const modal = document.getElementById("clientModal");
    const form = document.getElementById("clientForm");
    form.dataset.editId = id;
    form.querySelector('[name="nombre"]').value = cliente.nombre;
    form.querySelector('[name="correo"]').value = cliente.correo;
    modal.querySelector("h3").textContent = "Editar cliente";
    form.querySelector('[type="submit"]').textContent = "Actualizar cliente";
    modal.showModal();
}

function openProductEditor(id) {
    const producto = state.productos.find(item => item.id === id);
    const modal = document.getElementById("productModal");
    const form = document.getElementById("productForm");
    form.dataset.editId = id;
    form.querySelector('[name="nombre"]').value = producto.nombre;
    form.querySelector('[name="precio"]').value = producto.precio;
    form.querySelector('[name="stock"]').value = producto.stock;
    modal.querySelector("h3").textContent = "Editar producto";
    form.querySelector('[type="submit"]').textContent = "Actualizar producto";
    modal.showModal();
}

function openOrderEditor(id) {
    const pedido = state.pedidos.find(item => item.id === id);
    const modal = document.getElementById("orderModal");
    const form = document.getElementById("orderForm");
    form.dataset.editId = id;
    form.querySelector('[name="cliente_id"]').value = pedido.cliente_id;
    form.querySelector('[name="estado"]').value = pedido.estado;
    document.getElementById("orderProductField").hidden = true;
    document.getElementById("orderQuantityField").hidden = true;
    document.getElementById("orderStateField").hidden = false;
    form.querySelector('[name="producto_id"]').disabled = true;
    form.querySelector('[name="cantidad"]').disabled = true;
    modal.querySelector("h3").textContent = "Editar pedido";
    form.querySelector('[type="submit"]').textContent = "Actualizar pedido";
    modal.showModal();
}

async function deleteRecord(url, message) {
    try {
        await request(url, { method: "DELETE" });
        toast(message);
        await loadData();
    } catch (error) {
        toast(error.message);
    }
}

document.getElementById("clientModal").addEventListener("close", resetClientModal);
document.getElementById("productModal").addEventListener("close", resetProductModal);
document.getElementById("orderModal").addEventListener("close", resetOrderModal);

function resetClientModal() {
    const form = document.getElementById("clientForm");
    delete form.dataset.editId;
    form.reset();
    document.querySelector("#clientModal h3").textContent = "Nuevo cliente";
    form.querySelector('[type="submit"]').textContent = "Guardar cliente";
}

function resetProductModal() {
    const form = document.getElementById("productForm");
    delete form.dataset.editId;
    form.reset();
    document.querySelector("#productModal h3").textContent = "Nuevo producto";
    form.querySelector('[type="submit"]').textContent = "Guardar producto";
}

function resetOrderModal() {
    const form = document.getElementById("orderForm");
    delete form.dataset.editId;
    form.reset();
    document.getElementById("orderProductField").hidden = false;
    document.getElementById("orderQuantityField").hidden = false;
    document.getElementById("orderStateField").hidden = true;
    form.querySelector('[name="producto_id"]').disabled = false;
    form.querySelector('[name="cantidad"]').disabled = false;
    document.querySelector("#orderModal h3").textContent = "Nuevo pedido";
    form.querySelector('[type="submit"]').textContent = "Crear pedido";
    form.querySelector('[name="cantidad"]').value = 1;
}

document.getElementById("clientForm").addEventListener("submit", async event => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
        const editId = event.target.dataset.editId;
        await request(editId ? `/clientes/${editId}` : "/clientes", {
            method: editId ? "PATCH" : "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nombre: form.get("nombre"), correo: form.get("correo") }),
        });
        event.target.reset();
        event.target.closest("dialog").close();
        toast(editId ? "Cliente actualizado correctamente" : "Cliente creado correctamente");
        await loadData();
    } catch (error) {
        toast(error.message);
    }
});

document.getElementById("productForm").addEventListener("submit", async event => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
        const editId = event.target.dataset.editId;
        await request(editId ? `/productos/${editId}` : "/productos", {
            method: editId ? "PATCH" : "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                nombre: form.get("nombre"),
                precio: Number(form.get("precio")),
                stock: Number(form.get("stock")),
            }),
        });
        event.target.reset();
        event.target.closest("dialog").close();
        toast(editId ? "Producto actualizado correctamente" : "Producto creado correctamente");
        await loadData();
    } catch (error) {
        toast(error.message);
    }
});

document.getElementById("orderForm").addEventListener("submit", async event => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
        const editId = event.target.dataset.editId;
        await request(editId ? `/pedidos/${editId}` : "/pedidos", {
            method: editId ? "PATCH" : "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(editId ? {
                cliente_id: Number(form.get("cliente_id")),
                estado: form.get("estado"),
            } : {
                cliente_id: Number(form.get("cliente_id")),
                items: [{
                    producto_id: Number(form.get("producto_id")),
                    cantidad: Number(form.get("cantidad")),
                }],
            }),
        });
        event.target.reset();
        event.target.closest("dialog").close();
        toast(editId ? "Pedido actualizado correctamente" : "Pedido creado correctamente");
        await loadData();
    } catch (error) {
        toast(error.message);
    }
});

loadData();
