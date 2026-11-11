// The page talks to one origin only (/api/...) — nginx forwards each prefix to the
// service that owns it. Every path here is the one api-gateway will serve in Step 5.

const state = {
  user: localStorage.getItem("shopstream.user") || "guest",
  cart: { userId: "guest", items: [], totalQuantity: 0 },
  products: new Map(),      // id -> product, for the names in the cart
  categories: new Set(),
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const text = await res.text();
  let body = null;
  if (text) { try { body = JSON.parse(text); } catch { body = text; } }
  if (!res.ok) {
    const detail = (body && (body.detail || body.message)) || res.status + " " + res.statusText;
    throw new Error(detail);
  }
  return body;
}

const money = (n) => "€" + Number(n || 0).toFixed(2);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function toast(message, bad = false) {
  const el = $("toast");
  el.textContent = message;
  el.className = "toast show" + (bad ? " bad" : "");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (el.className = "toast"), 2200);
}

/* ---------------- navigation ---------------- */

function setView(name) {
  if (location.hash.slice(1) !== name) history.replaceState(null, "", "#" + name);
  for (const section of document.querySelectorAll(".view")) section.classList.add("hidden");
  $("view-" + name).classList.remove("hidden");
  for (const tab of document.querySelectorAll(".tab")) tab.classList.toggle("active", tab.dataset.view === name);
  if (name === "cart") loadCart();
  if (name === "orders") renderRecent();
}

/* ---------------- catalogue ---------------- */

function stockBadge(stock) {
  if (stock <= 0) return '<span class="badge stock-out">out of stock</span>';
  if (stock < 5) return '<span class="badge stock-low">only ' + stock + " left</span>";
  return '<span class="badge stock-ok">' + stock + " in stock</span>";
}

function renderGrid(items, total) {
  const grid = $("grid");
  grid.innerHTML = items.map((p) => `
    <article class="card">
      <div class="row">
        <div>
          <div class="name">${esc(p.name)}</div>
          <span class="badge">${esc(p.category)}</span>
        </div>
        ${stockBadge(p.stock)}
      </div>
      <p class="desc">${esc(p.description)}</p>
      <div class="foot">
        <span class="price">${money(p.price)}</span>
        <button class="primary add" data-id="${p.id}" ${p.stock <= 0 ? "disabled" : ""}>Add to cart</button>
      </div>
    </article>`).join("");

  for (const btn of grid.querySelectorAll(".add")) {
    btn.onclick = () => addToCart(Number(btn.dataset.id), btn);
  }

  $("result-line").textContent = total === 0
    ? "Nothing matched. Try a broader search."
    : total + (total === 1 ? " product" : " products") + " in the catalogue";
}

async function loadCatalogue() {
  const params = new URLSearchParams();
  const q = $("q").value.trim();
  const category = $("category").value;
  const min = $("min-price").value;
  const max = $("max-price").value;
  if (q) params.set("q", q);
  if (category) params.set("category", category);
  if (min) params.set("minPrice", min);
  if (max) params.set("maxPrice", max);
  params.set("size", "24");

  try {
    const page = await api("/api/search?" + params);
    for (const p of page.items) {
      state.products.set(p.id, p);
      if (p.category) state.categories.add(p.category);
    }
    fillCategories();
    renderGrid(page.items, page.total);
    if (page.total > page.items.length) {
      $("result-line").textContent += " (showing the first " + page.items.length + ")";
    }
  } catch (err) {
    $("result-line").textContent = "The catalogue is unavailable: " + err.message;
  }
}

function fillCategories() {
  const select = $("category");
  const current = select.value;
  select.innerHTML = '<option value="">all categories</option>' +
    [...state.categories].sort().map((c) => '<option value="' + esc(c) + '">' + esc(c) + "</option>").join("");
  select.value = current;
}

/* ---------------- cart ---------------- */

async function refreshBadge() {
  try {
    const cart = await api("/api/carts/" + encodeURIComponent(state.user));
    state.cart = cart;
    $("cart-count").textContent = cart.totalQuantity;
    $("cart-key").textContent = "carts:" + state.user;
  } catch {
    $("cart-count").textContent = "0";
  }
}

async function addToCart(productId, button) {
  button.disabled = true;
  try {
    await api("/api/carts/" + encodeURIComponent(state.user) + "/items", {
      method: "POST",
      body: JSON.stringify({ productId, quantity: 1 }),
    });
    await refreshBadge();
    const p = state.products.get(productId);
    toast("Added " + (p ? p.name : "product " + productId) + " to the cart");
  } catch (err) {
    toast(err.message, true);
  } finally {
    button.disabled = false;
  }
}

async function productOf(id) {
  if (state.products.has(id)) return state.products.get(id);
  try {
    const p = await api("/api/products/" + id);
    state.products.set(id, p);
    return p;
  } catch {
    return { id, name: "product " + id, price: 0, stock: 0, removed: true };
  }
}

async function loadCart() {
  try {
    state.cart = await api("/api/carts/" + encodeURIComponent(state.user));
  } catch (err) {
    toast("The cart is unavailable: " + err.message, true);
    return;
  }
  $("cart-count").textContent = state.cart.totalQuantity;
  $("cart-key").textContent = "carts:" + state.user;
  await renderCart();
}

async function renderCart() {
  const items = state.cart.items || [];
  $("cart-empty").classList.toggle("hidden", items.length > 0);
  $("cart-table").classList.toggle("hidden", items.length === 0);

  const rows = [];
  let total = 0;
  for (const line of items) {
    const p = await productOf(line.productId);
    const price = Number(p.price || 0);
    const lineTotal = price * line.quantity;
    total += lineTotal;
    rows.push(`
      <div class="cart-row">
        <div>
          <div class="item-name">${esc(p.name)}</div>
          <div class="item-id">product #${line.productId}${p.removed ? " — removed from the catalogue" : ""}</div>
        </div>
        <div>${money(price)}</div>
        <div class="qty">
          <button data-act="dec" data-id="${line.productId}">−</button>
          <span>${line.quantity}</span>
          <button data-act="inc" data-id="${line.productId}">+</button>
        </div>
        <div>${money(lineTotal)}</div>
        <button class="ghost" data-act="remove" data-id="${line.productId}" title="remove">✕</button>
      </div>`);
  }
  $("cart-rows").innerHTML = rows.join("");
  $("cart-total").textContent = money(total);

  for (const btn of $("cart-rows").querySelectorAll("button")) {
    const id = Number(btn.dataset.id);
    const act = btn.dataset.act;
    btn.onclick = async () => {
      const line = items.find((i) => i.productId === id);
      try {
        if (act === "remove") {
          await api("/api/carts/" + encodeURIComponent(state.user) + "/items/" + id, { method: "DELETE" });
        } else {
          const quantity = line.quantity + (act === "inc" ? 1 : -1);
          if (quantity <= 0) {
            await api("/api/carts/" + encodeURIComponent(state.user) + "/items/" + id, { method: "DELETE" });
          } else {
            await api("/api/carts/" + encodeURIComponent(state.user) + "/items/" + id, {
              method: "PUT",
              body: JSON.stringify({ quantity }),
            });
          }
        }
        await loadCart();
      } catch (err) {
        toast(err.message, true);
      }
    };
  }
}

async function clearCart() {
  try {
    await api("/api/carts/" + encodeURIComponent(state.user), { method: "DELETE" });
    await loadCart();
    toast("Cart cleared");
  } catch (err) {
    toast(err.message, true);
  }
}

function banner(kind, text) {
  const el = $("cart-banner");
  el.className = "banner " + kind;
  el.innerHTML = text;
}

async function checkout() {
  const btn = $("checkout");
  btn.disabled = true;
  btn.textContent = "Placing order…";
  banner("wait", "Posting the cart to order-service and waiting for the stock reservation…");
  try {
    const result = await api("/api/carts/" + encodeURIComponent(state.user) + "/checkout", { method: "POST" });
    if (result.orderStatus === "CONFIRMED") {
      banner("ok", "<strong>Order #" + result.orderId + " confirmed.</strong> The stock was reserved and the cart was cleared.");
    } else if (result.orderStatus === "REJECTED") {
      banner("bad", "<strong>Order #" + result.orderId + " rejected.</strong> " + esc(result.message) + " Your cart was kept, so you can adjust it.");
    } else {
      banner("wait", "<strong>Order #" + result.orderId + " is still " + result.orderStatus + ".</strong> " + esc(result.message) + " The cart was kept.");
    }
    remember(result.orderId);
    await loadCart();
    await trackOrder(result.orderId, true);
    setView("orders");
  } catch (err) {
    banner("bad", "<strong>Checkout failed.</strong> " + esc(err.message) + " The cart was kept.");
  } finally {
    btn.disabled = false;
    btn.textContent = "Checkout →";
  }
}

/* ---------------- orders ---------------- */

function recent() {
  try { return JSON.parse(localStorage.getItem("shopstream.orders") || "[]"); } catch { return []; }
}

function remember(id) {
  const list = recent().filter((x) => x !== id);
  list.unshift(id);
  localStorage.setItem("shopstream.orders", JSON.stringify(list.slice(0, 8)));
  renderRecent();
}

function renderRecent() {
  const list = recent();
  $("recent").innerHTML = list.length
    ? list.map((id) => '<button data-id="' + id + '">Order #' + id + "</button>").join("")
    : '<span class="muted">none yet</span>';
  for (const btn of $("recent").querySelectorAll("button")) {
    btn.onclick = () => trackOrder(Number(btn.dataset.id), true);
  }
}

function renderOrder(order) {
  const lines = (order.items || []).map((i) => `
    <div class="order-line">
      <span>product #${i.productId} × ${i.quantity}</span>
      <span>${money(i.unitPrice)} each</span>
    </div>`).join("");
  $("order-card").innerHTML = `
    <div class="order-card">
      <div class="order-head">
        <span class="id">Order #${order.id}</span>
        <span class="status ${order.status}">${order.status}</span>
      </div>
      <p class="muted">placed ${new Date(order.createdAt).toLocaleString()}</p>
      ${lines}
      <div class="order-total"><span>Total</span><span>${money(order.totalPrice)}</span></div>
    </div>`;
}

async function trackOrder(id, scroll) {
  $("order-id").value = id;
  try {
    let order = await api("/api/orders/" + id);
    renderOrder(order);
    remember(order.id);
    if (scroll) $("order-card").scrollIntoView({ behavior: "smooth", block: "nearest" });

    // PENDING is normal for a moment: the answer comes back over Kafka.
    for (let i = 0; i < 14 && order.status === "PENDING"; i++) {
      await new Promise((r) => setTimeout(r, 1500));
      order = await api("/api/orders/" + id);
      renderOrder(order);
    }
  } catch (err) {
    $("order-card").innerHTML = '<div class="banner bad">' + esc(err.message) + "</div>";
  }
}

/* ---------------- wiring ---------------- */

$("user-id").value = state.user;
$("user-id").onchange = () => {
  state.user = ($("user-id").value.trim() || "guest");
  localStorage.setItem("shopstream.user", state.user);
  refreshBadge();
  if (!$("view-cart").classList.contains("hidden")) loadCart();
};

for (const tab of document.querySelectorAll(".tab")) tab.onclick = () => setView(tab.dataset.view);
$("search").onclick = loadCatalogue;
$("reset").onclick = () => {
  $("q").value = ""; $("category").value = ""; $("min-price").value = ""; $("max-price").value = "";
  loadCatalogue();
};
$("q").onkeydown = (e) => { if (e.key === "Enter") loadCatalogue(); };
$("category").onchange = loadCatalogue;
$("clear-cart").onclick = clearCart;
$("checkout").onclick = checkout;
$("track").onclick = () => {
  const id = Number($("order-id").value);
  if (id > 0) trackOrder(id, true); else toast("Enter an order id first", true);
};
$("order-id").onkeydown = (e) => { if (e.key === "Enter") $("track").click(); };

// #cart, #orders and #orders/7 are real links: a refresh (or a demo script) lands on the same view.
const [initialView, initialId] = location.hash.slice(1).split("/");
if (["store", "cart", "orders"].includes(initialView)) setView(initialView);
if (initialView === "orders" && Number(initialId) > 0) trackOrder(Number(initialId), false);

loadCatalogue();
refreshBadge();