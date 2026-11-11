# Development Notes

An engineering log for the semester project. It records **what was decided, why, and what broke**,
so that the written report can be assembled from it without reconstructing history from memory.

---

## 1. Project facts

| Item | Value |
|---|---|
| Course | Development of Distributed Web Applications |
| Instructor | Fadi Atallah (GitHub: `Fadi-97`) |
| System | ShopStream — distributed e-commerce platform |
| Deadline (code + report) | Friday, 4 December 2026 |
| Presentation | Wednesday, 9 December 2026, 15 minutes |
| Stack | Java 21, Spring Boot 3.3.4, MySQL 8.4, Kafka 3.7 (`cp-kafka` 7.6.1, KRaft), Docker Compose |

---

## 2. Working environment

| Tool | Version | Notes |
|---|---|---|
| git | 2.53.0 | commit identity `ChenZizheng <chen.zizheng@student.uni-miskolc.hu>` |
| Docker | 29.8.0 (Desktop) | Linux containers |
| gh | 2.103.3 | installed to `%LOCALAPPDATA%\Programs\gh\bin` |
| JDK | **none on the host** | JDK 21 is only used inside the build container |

There is no JDK installed on the developer machine. This is not a blocker: the Dockerfiles build
with a Maven image, so `docker compose up --build` compiles, tests and packages everything inside
the container. A local JDK is only needed for IDE support (debugging, red squiggles).

---

## 3. Step 1 — Docker

### 3.1 Architecture

```
        :8080                    :8081
   +-------------+          +-------------+
   |product-svc  |<--HTTP---| order-svc   |
   +------+------+  prices  +------+------+
          |                        |
     mysql-product            mysql-order
     (named volume)           (named volume)
```

Two services, two databases, one `docker compose up`.

### 3.2 Decisions and rationale

**Database per service.** Each service owns its schema and no service ever reads another one's
tables. This is the requirement, and it is also what makes the later steps possible: once a service
cannot `JOIN` against foreign data, the only ways left to get it are REST and Kafka — which is
exactly the architecture the course is about. `mysql-product` and `mysql-order` are separate
containers with separate named volumes.

**The client never sends prices.** `POST /orders` accepts only `{productId, quantity}`. order-service
asks product-service for the current price of every line and sums the total itself. If the client
supplied `unitPrice`, a customer could order a laptop for one forint; the price is a trust boundary,
so it must be resolved server-side. This also makes the HTTP call in the requirement a real
dependency rather than decoration.

**Everything is an environment variable.** No connection string, hostname or credential is
hard-coded. `application.yml` reads `${DB_URL}`, `${DB_USER}`, `${DB_PASSWORD}`,
`${PRODUCT_SERVICE_URL}`, and compose supplies them. The requirement forbids `localhost` inside a
container, and the reason is concrete: inside a container `localhost` is the container itself, so
`jdbc:mysql://localhost:3306` would try to reach a database that is not there. Compose service names
(`mysql-product`, `product-service`) resolve through Docker's embedded DNS.

**Multi-stage Docker build.** `maven:3.9-eclipse-temurin-21` compiles, `eclipse-temurin:21-jre` runs.
`pom.xml` is copied and `mvn dependency:go-offline` runs *before* `COPY src`, so a source-only change
does not re-download the whole dependency tree. The runtime image contains a JRE, not a JDK, and not
Maven — it is roughly a third of the size and has no compiler for an attacker to use.

**`depends_on` with `condition: service_healthy`.** A plain `depends_on` only waits for the container
to *start*, and MySQL takes several seconds to accept connections. Without the healthcheck the
services race the database on every cold start. `mysqladmin ping` is the probe; the service waits for
`service_healthy`, order-service waits for product-service with `service_started`.

**Named volumes.** `docker compose down` must not destroy the data, `docker compose down -v` must.
Named volumes give that separation; bind mounts would tie the data to a host path.

**Errors as RFC 7807 `ProblemDetail`.** Spring Boot 3 returns structured problem+json for validation
failures and 404s instead of a stack trace, which keeps the API contract honest and is what a
gateway/front-end would consume later.

**Orders start as `PENDING`.** In Step 1 nothing consumes the order, so it could arguably be
`CONFIRMED` immediately. It is left `PENDING` on purpose because Step 2 introduces the Kafka
saga (OrderPlaced → StockReserved/StockRejected → CONFIRMED/REJECTED) and the state machine should
not have to be retrofitted.

### 3.3 Problems encountered

| Problem | Cause | Fix |
|---|---|---|
| No JDK on the host | never installed | multi-stage Docker build; Maven runs in the container |
| Services crashed on cold start | MySQL not ready when the app connected | `healthcheck: mysqladmin ping` + `depends_on: condition: service_healthy` |
| Placeholder image in the build | `slim` JRE tag has no `curl` for healthchecks | healthchecks run in the MySQL container, not the app container |
| `order-service` pom still said `product-service` | copy-paste | fixed the `<name>` and `<artifactId>` |

---

## 4. Step 2 — Kafka

### 4.1 Architecture

```
   order-service                    product-service
   ┌────────────┐   OrderPlaced    ┌──────────────────┐
   │ POST       │ ───order-events─>│ InventoryService │
   │ /orders    │                  │ reserve()        │
   │ PENDING    │<─inventory-events─│ one transaction  │
   └────────────┘   StockReserved  └──────────────────┘
        │           StockRejected           
        │                 │
        └─────┬───────────┘
              ▼
      notification-service  →  one "e-mail" per finished order
```

Single broker in KRaft mode (`confluentinc/cp-kafka:7.6.1`), three topics with three partitions each.

### 4.2 Decisions and rationale

**KRaft, not ZooKeeper.** Kafka 3.x can run without ZooKeeper: the broker also takes the controller
role and the cluster metadata lives in the Kafka log itself. The course only asks for "a Kafka broker";
adding a second container that exists purely to elect the first would be one more thing to start, to
health-check and to explain. One container, one `CLUSTER_ID`, done.

**The event contract is a duplicated package, not a shared library.** Every service carries its own
copy of `hu.unimiskolc.shopstream.events`. A shared jar would couple the build of three services and
turn "deploy product-service alone" into a version-negotiation problem. The copies are safe because
the class names are identical, and identical class names are exactly what the JSON type header needs:
Spring Kafka's `JsonSerializer` writes `__TypeId__` = the fully qualified class name into the record
headers, and the consumer resolves that name against its own classpath.

**JSON with type headers, and a trusted-package allow-list.** JSON makes the messages readable in
`kafka-console-consumer` during the demo, which is worth more than the compactness of Avro. The
`spring.json.trusted.packages` setting is not cosmetic: a deserializer that instantiates whatever class
name a record header names is a remote-code-instantiation hole, so only our own event package is
allowed.

**Key = `orderId`.** Kafka only guarantees order *within a partition*. Both order topics are keyed by
`orderId`, so all events of one order land on the same partition and are consumed in the order they
were produced — which is what makes "Placed before Reserved" a guarantee instead of a hope. Three
partitions give parallelism across orders; the key gives serialisation within an order.

**Explicit topics, auto-creation off.** `KafkaTopicConfig` declares the topics with `TopicBuilder`
(3 partitions, replication factor 1) and the broker runs with `KAFKA_AUTO_CREATE_TOPICS_ENABLE=false`.
If auto-creation were on, the first producer to touch a mistyped topic name would silently create it
with the broker default of one partition, and the mistake would only appear under load.

**Publish after commit, not inside the transaction.** `order-service` publishes `OrderPlaced` from a
`@TransactionalEventListener(phase = AFTER_COMMIT)`. Sending inside the transaction is faster but can
announce an order whose insert is later rolled back — the events and the database would disagree, with
no way to detect it. Same reasoning on the product side: `reserve()` returns only after its
transaction commits, and the listener publishes the result afterwards.

**Idempotent stock reservation.** Kafka is at-least-once, so the same `OrderPlaced` *will* arrive twice
sooner or later (restart, rebalance, retry). `processed_orders` stores one row per handled order, and
`reserve()` short-circuits on a known `orderId`, returning the original outcome. The check, the stock
decrement and the row insert happen in one transaction, so a crash mid-way rolls all three back and the
redelivered message starts from a clean state.

**HTTP for prices, Kafka for stock.** Two different questions, two different mechanisms. The price is
needed *now*, to answer the client and to freeze the amount in the order — a request that must fail
loudly if product-service is down. The stock reservation is a decision that can be made a second later,
and making it asynchronous is what removes the distributed transaction: order-service never needs to
know whether stock exists, it only reacts to the answer.

**One topic, three record types, dispatched on the payload.** The brief puts `OrderPlaced`,
`OrderConfirmed` and `OrderRejected` on the same topic, so a listener cannot rely on the topic to tell
it what arrived. The JSON type header decides which record the deserializer builds, and each listener
dispatches on the value: product-service acts on `OrderPlaced` and ignores the two answers it produced
itself, notification-service records `OrderPlaced` and mails on the terminal events. The alternative —
three topics — would contradict the event table in the brief and triple the topic count.

**The e-mail is triggered by the order event, not by the stock event.** Both `OrderPlaced` and the
terminal `OrderConfirmed`/`OrderRejected` carry the order id as key, so they arrive on one partition,
in order, on one consumer: the content of the order is always known before its status. Reading the
status from `inventory-events` instead would have needed a wait for the other topic to catch up
(the first version did exactly that, with a 2-second timeout) — ordering within a topic is a
guarantee, ordering across two topics is not.

**notification-service keeps its state in memory.** It needs no database: it buffers the last
`OrderPlaced` per order and sends one mail per terminal *order* event, deduplicated in a set. A
persistent store would be the correct choice if a mail could be lost on restart; for a simulated mail
that writes a log line, it would be ceremony.

**Consumer groups per service.** `product-service`, `order-service` and `notification-service` each use
their own group id, so each sees every event (broadcast between services) while a second instance of the
same service would split the partitions with the first (load balancing inside a service).

### 4.3 Problems encountered

| Problem | Cause | Fix |
|---|---|---|
| `__TypeId__` not found on the consumer | event classes in different packages per service | one shared package name, duplicated verbatim into each service |
| No JDK to compile locally | host has none | same multi-stage Docker build; the Kafka changes are compiled inside the image |
| `KafkaTemplate` injection ambiguity | `KafkaTemplate<Object,Object>` vs the auto-configured `KafkaTemplate<?,?>` | inject `KafkaTemplate<Object, Object>`; the wildcard bean matches by raw type |
| MySQL dialect warning (HHH90000025) | explicit `hibernate.dialect` in `application.yml` | removed; Hibernate detects the dialect from the connection |
| `notification-service` crashed on startup | `spring-kafka` does not bring `jackson-databind`, and `JsonDeserializer` needs it (`NoClassDefFoundError: com/fasterxml/jackson/databind/JavaType`) | added `spring-boot-starter-json` to its pom |
| console-producer replay rejected the line | with `parse.headers=true` the headers are separated from key and value by a **tab**, not by `\|` | built the line with tab characters |
| `order-events` only ever carried `OrderPlaced` | the saga set the status in its own database but announced nothing, so the event table in the brief was only half implemented | added `OrderConfirmed` and `OrderRejected` and one `OrderEventsPublisher` that sends all three after commit |
| listener with an `Object` parameter matched nothing | Spring Kafka hands the whole `ConsumerRecord` to a parameter typed `Object`, so `instanceof OrderPlaced` was always false: no error, offset committed, order silently stuck in `PENDING` | the listeners take `ConsumerRecord<String, Object>` and inspect `value()` |

### 4.4 Verification (observed, not assumed)

Run after `docker compose down -v` and `docker compose up --build`, so every line below comes from an
empty database and an empty Kafka log.

| Check | Result |
|---|---|
| start from nothing | six containers up, databases empty, topics created by `KafkaTopicConfig` |
| topic layout | `kafka-topics --describe`: `order-events`, `inventory-events`, `product-events`, `PartitionCount: 3`, `ReplicationFactor: 1` |
| order 1: 2 x product 1 (stock 5, 89.90) | POST → `PENDING`, `totalPrice 179.80`; then `CONFIRMED`; stock 5 → 3 |
| order 2: 5 x product 2 (stock 2, 79.90) | POST → `PENDING`, `totalPrice 399.50`; then `REJECTED`, reason `Insufficient stock for product 2: requested 5, available 2`; stock unchanged |
| order-events content | `OrderPlaced` + `OrderConfirmed` for order 1, `OrderPlaced` + `OrderRejected` for order 2, each with its `__TypeId__` header |
| notification-service | two mails: order #1 confirmed with total and items, order #2 rejected with the reason |
| replay of the same `OrderPlaced` (earlier run, order 4) | stock unchanged; log: `Order 4 was already processed as STOCK_RESERVED - stock untouched (idempotent delivery)` |

---

## 5. Step 3 — Elasticsearch

### 5.1 Architecture

```
   product-service                 search-service              elasticsearch
   ┌──────────────┐  product-events ┌───────────────┐  index   ┌──────────────┐
   │ ProductCtrl  │ ──────────────> │ ProductIndex  │ ───────> │ products     │
   │ create/update│  key=productId  │ Listener      │  write   │ (text/keyword│
   │ /delete      │                 │               │          │  /double/int)│
   └──────────────┘                 │ /search ──────┼────────> │              │
                                    └───────────────┘  query   └──────────────┘
```

The index is fed only by the event stream; nobody reads product-service's tables.

### 5.2 Decisions and rationale

**The read model is built from events, not from the database.** The rule "a service never reads another
service's database" leaves exactly one channel for the catalogue: `product-events`. search-service
therefore owns a *copy* of the product data shaped for searching, and product-service owns the original.
The cost is eventual consistency — a product is searchable a few hundred milliseconds after it is
created — and the benefit is that the search service can be rebuilt from scratch at any time by
replaying the topic (its consumer group starts at `earliest`, so an empty index refills itself).

**An explicit mapping, not dynamic mapping.** Left to itself Elasticsearch guesses: `name` would become
`text` with a `keyword` sub-field, `category` would become `text`, `price` might become `float` or
`long`. Guessed types are decided by the *first* document that arrives and are painful to change later.
The mapping is declared with `@Field`, because the type is what makes a query possible: `text` for the
two fields people type into, `keyword` for the field people filter on (an analysed `text` cannot be
matched exactly), `double` for money and `integer` for stock so range filters behave numerically.

**The index is created at startup if it is missing.** `IndexInitializer` runs as an `ApplicationRunner`,
asks `IndexOperations` whether `products` exists and calls `createWithMapping()` if not. Without it the
first query against a fresh cluster fails with `index_not_found_exception` — an empty result set and a
missing index look the same to a user but are very different to a demo.

**The document is a separate class from the entity.** `ProductDocument` has no JPA annotations and
search-service never imports product-service's `Product`. The only thing the two services share is the
event package (`ProductCreated`, `ProductUpdated`, `ProductDeleted`, `Topics`), duplicated verbatim.
A shared entity would couple the two schemas, which is the coupling the whole architecture is avoiding.

**Full text in `must`, filters in `filter`.** `q` goes through `multiMatch` over `name` and
`description` inside `must`, so hits are *scored* and the best match comes first. `category` and the
price window go inside `filter`, where clauses are boolean-only: they do not influence the score, and
Elasticsearch can cache them. Putting `category` in `must` would make a cheap term match outrank a good
text match.

**`bool.build()._toQuery()`.** The Java client's `BoolQuery.Builder.build()` returns `BoolQuery`, not the
`Query` that `withQuery()` wants. The bridge is the generated `_toQuery()` method; there is no implicit
conversion, and the compiler only says `cannot find symbol: method toQuery()`.

**The controller validates its own input.** `page < 0`, `size <= 0`, `size > 100` and
`minPrice > maxPrice` are rejected with `400` and a problem+json body before anything reaches
Elasticsearch — a negative page would otherwise surface as a 500 from the client library, and an
unbounded `size` is a trivial way to ask the cluster for the entire index.

**Stock freshness.** A reservation changes stock in product-service's database; the index would keep
the old number forever. After publishing `StockReserved`, product-service re-reads the touched products
and publishes `ProductUpdated`, so the index converges without search-service ever calling back into
product-service (which would put a synchronous dependency in the read path).

### 5.3 Problems encountered

| Problem | Cause | Fix |
|---|---|---|
| `search-service` image build failed with no diagnostic | the Dockerfile runs `mvn -B -q`, and `-q` hides the compiler error | ran the same build in a bare `maven:3.9-eclipse-temurin-21` container without `-q` |
| `cannot find symbol: method toQuery()` at `ProductSearchService.java:65` | `BoolQuery.Builder.build()` returns `BoolQuery`, which is not a `Query` | `bool.build()._toQuery()` |

### 5.4 Verification (observed, not assumed)

| Check | Result |
|---|---|
| `GET :9200/products/_mapping` | `name`/`description` = `text`, `category` = `keyword`, `price` = `double`, `stock` = `integer` |
| create a product | `ProductCreated published for product 3` → 4 s later `GET :8082/search?q=keyboard` returned 1 hit |
| description-only word | `?q=brown` (present only in `description`, not in `name`) returned the same product → analysis works |
| `?category=peripherals&minPrice=50&maxPrice=100` | 1 hit; `?category=audio` → `total: 0` |
| `PUT /products/3` (price 89.90 → 79.90, stock 25 → 30) | search returned `price 79.9`, `stock 30` after 3 s |
| `POST /orders` 2 x product 3 | order `PENDING` (`totalPrice 159.80`) → search `stock 28` after 6 s → order `CONFIRMED` |
| `DELETE /products/3` | `ProductDeleted published` → `Removed product 3 from the index` → `total: 0` |
| invalid paging / price window | `?size=0` → `400`; `?minPrice=200&maxPrice=100` → `400` |

---

## 6. Step 4 — Redis

### 6.1 Where Redis sits

```
client ──> cart-service ──(hash carts:{userId})──> redis
               │  POST /orders (same call order-service already had)
               ▼
          order-service ──(events)──> product-service ──> kafka
               ▲                          │
               └──────── inventory-events┘

          product-service ──(GET /products/{id} cache)──> redis
```

Two unrelated uses of the same server: carts (the source of truth for one aggregate) and the product
read cache (a copy of MySQL that may be thrown away at any moment). They share a container, not a
lifetime.

### 6.2 Design decisions

**The cart's key is the user id.** `@RedisHash("carts")` + `@Id String userId` makes the repository key
`carts:{userId}`: `CrudRepository<Cart, String>` becomes sum/count style CRUD on a hash, and no
sequence, no `cart_id`, no lookup by user. Cart data is owned by cart-service, and MySQL is not involved
at all — the requirement is that each service owns its storage, not that every service owns a MySQL.

**The TTL is part of the model, not a cron job.** `@TimeToLive` on a `Long` field is written by Spring
Data Redis as `EXPIRE` on the hash, so Redis itself forgets the cart; there is no sweeper service and no
`deleted_at` column. Seven days is the number in `Cart.TTL_SECONDS` and in the README: long enough for a
customer to come back, short enough that abandoned carts do not accumulate forever. Every `save` rewrites
the TTL, so the clock measures inactivity.

**JSON in the hash.** The default `RedisTemplate` serializes with JDK serialization, which turns the hash
into binary that neither `redis-cli` nor a reviewer can read. cart-service declares its own
`RedisTemplate<String, Object>` — `StringRedisSerializer` for keys, `GenericJackson2JsonRedisSerializer`
for values — and a `redis-cli HGETALL carts:alice` is readable JSON.

**The cart stores no prices.** A price belongs to product-service; copying it into the cart would freeze a
stale number and would make cart-service depend on product-service's schema. Checkout sends only
`productId` + `quantity`, and order-service resolves the prices exactly as it does for a direct
`POST /orders` — one pricing path, not two.

**Checkout is a bounded wait, not a synchronous order.** `POST /orders` answers `PENDING` by design
(Step 2); the cart must be cleared only if the order is *accepted*. Making order-service block would undo
the asynchronous design, so cart-service polls `GET /orders/{id}` until the state is terminal or
`CHECKOUT_TIMEOUT_MS` (5 s) runs out. Three outcomes, and the cart is only deleted in the first:

| Order outcome | Cart | Answer |
|---|---|---|
| `CONFIRMED` | deleted | `cartCleared: true` |
| `REJECTED` | kept untouched | `cartCleared: false` + reason |
| still `PENDING` after 5 s | kept untouched | `cartCleared: false`, status reported |

Keeping the cart on rejection is the point: an out-of-stock line must not cost the customer the basket.
The trade-off is that a checkout that times out may still be confirmed a moment later, leaving a cart
whose order exists — acceptable for a demo, and it fails in the direction of "customer keeps their data".

**Eviction from the listener needed its own bean.** `OrderEventListener` evicts after `StockReserved`,
but Spring applies `@CacheEvict` through a proxy; calling an annotated method from another method of the
same object bypasses the proxy and evicts nothing. `ProductCache` is therefore a separate `@Component`
that the listener is given by the constructor. The cache TTL (10 minutes) is only a safety net for
whatever a bug might leave behind — correctness relies on the evictions.

**Redis has a password and a volume.** With `REDIS_PASSWORD` empty by default, the container would accept
unauthenticated writes from anything on the compose network; the password is in `.env` and both clients
pass it as `spring.data.redis.password`. AOF on a named volume means a restart does not silently empty
the carts (verified below); `down -v` is the explicit way to drop them.

### 6.3 Pitfalls

Three things that fail quietly rather than loudly, so each was checked on purpose:

| Pitfall | Why it is silent | Handling |
|---|---|---|
| JDK-serialized hash values | everything works; the data is simply unreadable outside the JVM | custom `RedisTemplate` with JSON values |
| `@CacheEvict` called from inside the same bean | no exception, the cache simply keeps the old entry | eviction moved to `ProductCache` |
| `docker compose exec redis redis-cli -a $REDIS_PASSWORD` | PowerShell expands `$REDIS_PASSWORD` before compose sees it, so redis-cli authenticates with an empty string and answers `NOAUTH` | quote it, or use `--no-auth-warning -a redispw` with the literal value |

### 6.4 Verification (observed, not assumed)

| Check | Result |
|---|---|
| `GET /carts/alice` on a new user | `{"userId":"alice","items":[],"totalQuantity":0}` — an empty cart, not a 404 |
| add 4 x2, then 5 x1, then 4 x1 | `items: [{4, 3}, {5, 1}]`, `totalQuantity: 4` — the duplicate line merged |
| `TTL carts:alice` / `HGETALL carts:alice` | `604800`, and the hash values are readable JSON |
| `PUT /items/4 {"quantity":5}` | `totalQuantity: 6`; `{"quantity":0}` → `400`; deleting an absent line → `404` |
| checkout a cart with 4 x5 | `{"orderId":4,"orderStatus":"CONFIRMED","cartCleared":true}`, order `totalPrice 449.50`, `EXISTS carts:alice` → `0` |
| checkout 4 x9999 (more than stock) | order `REJECTED`, `cartCleared: false`, cart still returned by `GET` |
| checkout an empty cart | `400` |
| cache fill / evict / refill | after `GET /products/5`: `products::5` with TTL 599; after `PUT`: key gone; next `GET` re-cached the new price |
| cache evicted by a reservation | after ordering one unit, `products::5` gone again and `GET` returned `stock 9` |
| `docker compose restart redis` with a cart in it | cart still there afterwards, `TTL` 604793 — AOF works |

---

## 7. The storefront

### 7.1 What it is

`frontend/` is three static files (`index.html`, `styles.css`, `app.js`) served by nginx, plus the nginx
that forwards `/api/*` to the services. It is not part of the five required steps — the PDF asks for a
distributed backend — but a system that can only be exercised with `Invoke-RestMethod` is hard to
demonstrate in fifteen minutes (and hard to be sure about while building it).

### 7.2 Decisions

**One origin, no CORS.** The obvious "open index.html and fetch four hosts" design needs a CORS exception
in four services, and a CORS exception is a permanent widening of every service's surface for the sake of
a demo page. Instead nginx serves the page and proxies the four prefixes, so the browser sees a single
origin and the services stay closed. The proxy is what api-gateway will do in Step 5, so the page's URLs
(`/api/products`, `/api/orders`, `/api/carts`, `/api/search`) were chosen to be the gateway's routes from
the start; moving the page onto the gateway changes no JavaScript.

**No build step.** No npm, no bundler, no framework: `COPY public/ /usr/share/nginx/html/` and it is
deployed. A frontend toolchain would put a Node build inside a project whose point is Docker + Spring, and
would be one more thing that can break in front of the examiner.

**The cart is rendered from references, not from copies.** cart-service stores `productId` and
`quantity` only, so the cart view resolves each name and price when it renders. That is visible in the
page's behaviour, not just in the API: change a price in the store and reload the cart, and the cart
already shows the new price — because it never had the old one.

**Checkout shows the wait.** `POST /carts/{id}/checkout` can block for up to five seconds while the order
waits for Kafka, so the button says *Placing order…* and the banner says what is being waited for instead
of looking frozen. The result message is the service's own: "cart cleared" or "order rejected, cart kept".
Then the page jumps to the order and keeps re-reading it while it is `PENDING`, which is how the
asynchronous sagas become visible rather than a mystery.

**Views are links.** `#store`, `#cart`, `#orders/8` are real URLs, so a refresh stays where it was and a
demo can jump straight to an order.

### 7.3 Problems encountered

| Problem | Cause | Fix |
|---|---|---|
| `GET /api/products` answered `301` to `/api/products/` (and the browser then failed to connect, because the redirect pointed at port 80 inside the network) | a `location /api/products/` block matches a prefix and nginx normalizes the missing slash | `location /api/products` — no trailing slash, so `proxy_pass` keeps the remainder |
| `GET /api/products/` answered `404` from Spring | Spring Boot 3 removed trailing-slash matching, so `/products/` is not `/products` | the same change; the page never asks for the slashed form |
| after `docker compose up -d --build frontend` the browser still served the old page | compose rebuilt the image but did not recreate the container, because the tag had not changed | `--force-recreate` (verified with `curl /styles.css | findstr nowrap`) |
| headless screenshots were blank | the page fills itself after `fetch`, and the screenshot was taken before the first response | `--virtual-time-budget=6000` |

### 7.4 Verification (observed, not assumed)

| Check | Result |
|---|---|
| `GET :8084/` | `200`, 3025 bytes of HTML; `styles.css` and `app.js` also `200` |
| `GET :8084/api/products` and `/api/products/6` | `200` with the product JSON — the proxy keeps the path |
| `GET :8084/api/search?q=headphones` | `{"total":1, ...}` |
| `GET :8084/api/carts/guest` | `{"userId":"guest","items":[],"totalQuantity":0}` |
| add two items in the page | badge showed `3`; `GET /api/carts/guest` showed `4 x2`, `6 x1`, total `€308.80` |
| `POST :8084/api/carts/guest/checkout` | `{"orderId":8,"orderStatus":"CONFIRMED","cartCleared":true}`; the cart was then empty and the order showed `totalPrice 308.80` |
| the same purchase in the search index | `stock` of product 6 went from 3 to 2 — the page's checkout went through the whole Kafka saga |
| screenshots | `docs/screenshots/{store,cart,orders}.png`, taken from a headless browser against the running stack |

---

## 8. Roadmap

| Step | Topic | Status |
|---|---|---|
| 1 | Docker: product-service, order-service, two MySQL databases | done |
| 2 | Kafka (KRaft): order-events, inventory-events, product-events; saga + idempotent stock | done |
| 3 | Elasticsearch: search-service, `products` index, full-text + filters | done |
| 4 | Redis: cart-service, `@RedisHash`, TTL, checkout; product cache | done |
| 5 | Spring Cloud: Eureka, Config Server, OpenFeign, Gateway, X-Request-Id | planned |