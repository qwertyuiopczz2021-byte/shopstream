// The page talks to one origin only (/api/...) — nginx forwards each prefix to the
// service that owns it. Every path here is the one api-gateway will serve in Step 5.
//
// Two languages, no framework: static text carries data-i18n keys, everything the
// script builds goes through t(). Switching language re-renders what is on screen.

const I18N = {
  en: {
    brand_tag: "demo storefront",
    nav_store: "Store",
    nav_cart: "Cart",
    nav_orders: "Orders",
    signed_in: "signed in as",

    search_ph: "Search the catalogue — name or description",
    all_categories: "all categories",
    min_ph: "min €",
    max_ph: "max €",
    btn_search: "Search",
    btn_reset: "Reset",
    loading: "loading…",

    products: "{n} products in the catalogue",
    product_one: "{n} product in the catalogue",
    no_match: "Nothing matched. Try a broader search.",
    showing_first: " (showing the first {n})",
    stock_ok: "{n} in stock",
    stock_low: "only {n} left",
    stock_out: "out of stock",
    add_to_cart: "Add to cart",
    catalogue_unavailable: "The catalogue is unavailable: {msg}",
    added_to_cart: "Added {name} to the cart",
    product_n: "product {n}",

    cart_title: "Your cart",
    cart_note: "Stored in Redis under <code>{key}</code>, with a 7 day TTL that every change resets.",
    cart_empty: "Your cart is empty. Pick something in the store.",
    col_item: "Item",
    col_price: "Price",
    col_qty: "Qty",
    col_total: "Total",
    total: "Total",
    btn_clear: "Clear cart",
    btn_checkout: "Checkout →",
    cart_cleared: "Cart cleared",
    cart_unavailable: "The cart is unavailable: {msg}",
    removed_from_catalogue: " — removed from the catalogue",
    remove: "remove",

    placing_order: "Placing order…",
    checkout_wait: "Posting the cart to order-service and waiting for the stock reservation…",
    checkout_confirmed: "<strong>Order #{id} confirmed.</strong> The stock was reserved and the cart was cleared.",
    checkout_rejected: "<strong>Order #{id} rejected.</strong> {msg} Your cart was kept, so you can adjust it.",
    checkout_pending: "<strong>Order #{id} is still {status}.</strong> {msg} The cart was kept.",
    checkout_failed: "<strong>Checkout failed.</strong> {msg} The cart was kept.",

    orders_title: "Orders",
    orders_note: "An order is answered as <code>PENDING</code> first: the stock question is settled by Kafka afterwards, and the status changes to <code>CONFIRMED</code> or <code>REJECTED</code>.",
    order_id_ph: "order id",
    btn_track: "Track order",
    recent_title: "Orders placed from this browser",
    recent_none: "none yet",
    order_placed: "placed {date}",
    order_line: "product #{id} × {qty}",
    each: "{price} each",
    enter_order_id: "Enter an order id first",

    status_PENDING: "PENDING",
    status_CONFIRMED: "CONFIRMED",
    status_REJECTED: "REJECTED",
  },
  zh: {
    brand_tag: "演示店铺",
    nav_store: "商店",
    nav_cart: "购物车",
    nav_orders: "订单",
    signed_in: "当前用户",

    search_ph: "搜索商品 —— 名称或描述",
    all_categories: "全部分类",
    min_ph: "最低 €",
    max_ph: "最高 €",
    btn_search: "搜索",
    btn_reset: "重置",
    loading: "加载中…",

    products: "共 {n} 件商品",
    product_one: "共 {n} 件商品",
    no_match: "没有匹配的商品，换个关键词试试。",
    showing_first: "（仅显示前 {n} 件）",
    stock_ok: "库存 {n}",
    stock_low: "仅剩 {n}",
    stock_out: "已售罄",
    add_to_cart: "加入购物车",
    catalogue_unavailable: "商品目录暂时不可用：{msg}",
    added_to_cart: "已把「{name}」加入购物车",
    product_n: "商品 {n}",

    cart_title: "你的购物车",
    cart_note: "存在 Redis 的 <code>{key}</code> 里，TTL 7 天，每次修改都会重新计时。",
    cart_empty: "购物车是空的，去商店挑点什么吧。",
    col_item: "商品",
    col_price: "单价",
    col_qty: "数量",
    col_total: "小计",
    total: "合计",
    btn_clear: "清空购物车",
    btn_checkout: "去结账 →",
    cart_cleared: "购物车已清空",
    cart_unavailable: "购物车暂时不可用：{msg}",
    removed_from_catalogue: " —— 已从商品目录移除",
    remove: "移除",

    placing_order: "正在下单…",
    checkout_wait: "正在把购物车交给 order-service，并等待库存预占结果…",
    checkout_confirmed: "<strong>订单 #{id} 已确认。</strong>库存已预占，购物车已清空。",
    checkout_rejected: "<strong>订单 #{id} 被拒绝。</strong>{msg} 购物车已为你保留，可以改完再试。",
    checkout_pending: "<strong>订单 #{id} 仍处于 {status}。</strong>{msg} 购物车已保留。",
    checkout_failed: "<strong>结账失败。</strong>{msg} 购物车已保留。",

    orders_title: "订单",
    orders_note: "下单时先返回 <code>PENDING</code>：库存问题由 Kafka 稍后决定，状态才会变成 <code>CONFIRMED</code> 或 <code>REJECTED</code>。",
    order_id_ph: "订单号",
    btn_track: "查询订单",
    recent_title: "本浏览器下过的订单",
    recent_none: "暂无",
    order_placed: "下单时间 {date}",
    order_line: "商品 #{id} × {qty}",
    each: "单价 {price}",
    enter_order_id: "请先输入订单号",

    status_PENDING: "待确认 PENDING",
    status_CONFIRMED: "已确认 CONFIRMED",
    status_REJECTED: "已拒绝 REJECTED",
  },
};

const state = {
  lang: localStorage.getItem("shopstream.lang") || (/^zh/i.test(navigator.language) ? "zh" : "en"),
  user: localStorage.getItem("shopstream.user") || "guest",
  cart: { userId: "guest", items: [], totalQuantity: 0 },
  products: new Map(),      // id -> product, for the names in the cart
  categories: new Set(),
  lastOrder: null,
};

const $ = (id) => document.getElementById(id);

function t(key, vars = {}) {
  const table = I18N[state.lang] || I18N.en;
  const text = table[key] ?? I18N.en[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, name) => (vars[name] ?? "{" + name + "}"));
}

const locale = () => (state.lang === "zh" ? "zh-CN" : "en-GB");
const money = (n) => "€" + Number(n || 0).toFixed(2);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

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

function toast(message, bad = false) {
  const el = $("toast");
  el.textContent = message;
  el.className = "toast show" + (bad ? " bad" : "");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (el.className = "toast"), 2200);
}

/* ---------------- language ---------------- */

function applyStatic() {
  document.documentElement.lang = state.lang === "zh" ? "zh-CN" : "en";
  for (const el of document.querySelectorAll("[data-i18n]")) el.textContent = t(el.dataset.i18n);
  for (const el of document.querySelectorAll("[data-i18n-ph]")) el.placeholder = t(el.dataset.i18nPh);
  $("lang").textContent = state.lang === "zh" ? "English" : "中文";
  $("cart-note").innerHTML = t("cart_note", { key: "carts:" + state.user });
  $("orders-note").innerHTML = t("orders_note");
}

function setLang(lang) {
  state.lang = lang;
  localStorage.setItem("shopstream.lang", lang);
  applyStatic();
  fillCategories();
  if (!$("view-store").classList.contains("hidden")) loadCatalogue();
  if (!$("view-cart").classList.contains("hidden")) loadCart();
  renderRecent();
  if (state.lastOrder) renderOrder(state.lastOrder);
  else if ($("order-id").value) trackOrder(Number($("order-id").value), false);
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
  if (stock <= 0) return '<span class="badge stock-out">' + t("stock_out") + "</span>";
  if (stock < 5) return '<span class="badge stock-low">' + t("stock_low", { n: stock }) + "</span>";
  return '<span class="badge stock-ok">' + t("stock_ok", { n: stock }) + "</span>";
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
        <button class="primary add" data-id="${p.id}" ${p.stock <= 0 ? "disabled" : ""}>${esc(t("add_to_cart"))}</button>
      </div>
    </article>`).join("");

  for (const btn of grid.querySelectorAll(".add")) {
    btn.onclick = () => addToCart(Number(btn.dataset.id), btn);
  }

  $("result-line").textContent = total === 0
    ? t("no_match")
    : t(total === 1 ? "product_one" : "products", { n: total }) +
      (total > items.length ? t("showing_first", { n: items.length }) : "");
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
  } catch (err) {
    $("result-line").textContent = t("catalogue_unavailable", { msg: err.message });
  }
}

function fillCategories() {
  const select = $("category");
  const current = select.value;
  select.innerHTML = '<option value="">' + esc(t("all_categories")) + "</option>" +
    [...state.categories].sort().map((c) => '<option value="' + esc(c) + '">' + esc(c) + "</option>").join("");
  select.value = current;
}

/* ---------------- cart ---------------- */

async function refreshBadge() {
  try {
    const cart = await api("/api/carts/" + encodeURIComponent(state.user));
    state.cart = cart;
    $("cart-count").textContent = cart.totalQuantity;
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
    toast(t("added_to_cart", { name: p ? p.name : t("product_n", { n: productId }) }));
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
    return { id, name: t("product_n", { n: id }), price: 0, stock: 0, removed: true };
  }
}

async function loadCart() {
  try {
    state.cart = await api("/api/carts/" + encodeURIComponent(state.user));
  } catch (err) {
    toast(t("cart_unavailable", { msg: err.message }), true);
    return;
  }
  $("cart-count").textContent = state.cart.totalQuantity;
  $("cart-note").innerHTML = t("cart_note", { key: "carts:" + state.user });
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
          <div class="item-id">${esc(t("product_n", { n: line.productId }))}${p.removed ? esc(t("removed_from_catalogue")) : ""}</div>
        </div>
        <div>${money(price)}</div>
        <div class="qty">
          <button data-act="dec" data-id="${line.productId}">−</button>
          <span>${line.quantity}</span>
          <button data-act="inc" data-id="${line.productId}">+</button>
        </div>
        <div>${money(lineTotal)}</div>
        <button class="ghost" data-act="remove" data-id="${line.productId}" title="${esc(t("remove"))}">✕</button>
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
    toast(t("cart_cleared"));
  } catch (err) {
    toast(err.message, true);
  }
}

function banner(kind, html) {
  const el = $("cart-banner");
  el.className = "banner " + kind;
  el.innerHTML = html;
}

async function checkout() {
  const btn = $("checkout");
  btn.disabled = true;
  btn.textContent = t("placing_order");
  banner("wait", t("checkout_wait"));
  try {
    const result = await api("/api/carts/" + encodeURIComponent(state.user) + "/checkout", { method: "POST" });
    if (result.orderStatus === "CONFIRMED") {
      banner("ok", t("checkout_confirmed", { id: result.orderId }));
    } else if (result.orderStatus === "REJECTED") {
      banner("bad", t("checkout_rejected", { id: result.orderId, msg: esc(result.message) }));
    } else {
      banner("wait", t("checkout_pending", { id: result.orderId, status: result.orderStatus, msg: esc(result.message) }));
    }
    remember(result.orderId);
    await loadCart();
    await trackOrder(result.orderId, true);
    setView("orders");
  } catch (err) {
    banner("bad", t("checkout_failed", { msg: esc(err.message) }));
  } finally {
    btn.disabled = false;
    btn.textContent = t("btn_checkout");
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
    ? list.map((id) => '<button data-id="' + id + '">#' + id + "</button>").join("")
    : '<span class="muted">' + esc(t("recent_none")) + "</span>";
  for (const btn of $("recent").querySelectorAll("button")) {
    btn.onclick = () => trackOrder(Number(btn.dataset.id), true);
  }
}

function renderOrder(order) {
  state.lastOrder = order;
  const lines = (order.items || []).map((i) => `
    <div class="order-line">
      <span>${esc(t("order_line", { id: i.productId, qty: i.quantity }))}</span>
      <span>${esc(t("each", { price: money(i.unitPrice) }))}</span>
    </div>`).join("");
  $("order-card").innerHTML = `
    <div class="order-card">
      <div class="order-head">
        <span class="id">#${order.id}</span>
        <span class="status ${order.status}">${esc(t("status_" + order.status))}</span>
      </div>
      <p class="muted">${esc(t("order_placed", { date: new Date(order.createdAt).toLocaleString(locale()) }))}</p>
      ${lines}
      <div class="order-total"><span>${esc(t("total"))}</span><span>${money(order.totalPrice)}</span></div>
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
  $("cart-note").innerHTML = t("cart_note", { key: "carts:" + state.user });
  refreshBadge();
  if (!$("view-cart").classList.contains("hidden")) loadCart();
};

$("lang").onclick = () => setLang(state.lang === "zh" ? "en" : "zh");

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
  if (id > 0) trackOrder(id, true); else toast(t("enter_order_id"), true);
};
$("order-id").onkeydown = (e) => { if (e.key === "Enter") $("track").click(); };

// ?lang=zh / ?lang=en overrides the stored choice, so a demo can open either version.
const forcedLang = new URLSearchParams(location.search).get("lang");
if (forcedLang === "zh" || forcedLang === "en") {
  state.lang = forcedLang;
  localStorage.setItem("shopstream.lang", forcedLang);
}

applyStatic();
fillCategories();

// #cart, #orders and #orders/7 are real links: a refresh (or a demo script) lands on the same view.
const [initialView, initialId] = location.hash.slice(1).split("/");
if (["store", "cart", "orders"].includes(initialView)) setView(initialView);
if (initialView === "orders" && Number(initialId) > 0) trackOrder(Number(initialId), false);

loadCatalogue();
refreshBadge();