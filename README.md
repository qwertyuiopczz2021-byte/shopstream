# ShopStream

Distributed e-commerce platform for the *Development of Distributed Web Applications* semester project.

**Current state: Step 4 — Redis (plus a storefront to look at).** Five Spring Boot services, one KRaft
Kafka broker, one Elasticsearch node, one Redis and a small web page. Orders are confirmed or rejected asynchronously through events, stock is decremented
exactly once, the catalogue is searchable with full-text queries and filters, carts live in Redis with a
TTL and are only emptied when the order they produce is confirmed, and the hot product reads are cached.

![The storefront](docs/screenshots/store.png)

Open **<http://localhost:8084>** after `docker compose up`: that is the whole system in a browser —
browse the catalogue, add to the cart, check out and watch the order come back `CONFIRMED`.

## Services

| Service | Host port | Container port | Database | Role |
|---|---|---|---|---|
| product-service | 8080 | 8080 | `products` (mysql-product) | product CRUD, reserves stock |
| order-service   | 8081 | 8080 | `orders` (mysql-order)     | places orders, tracks their state |
| cart-service | 8083 | 8080 | none (cart lives in redis) | carts per user, checkout into an order |
| notification-service | — | — | none | writes one simulated e-mail per finished order |
| search-service | 8082 | 8080 | none (index lives in elasticsearch) | full-text product search, filters, pagination |
| elasticsearch | — | 9200 | — | single node, `products` index |
| redis | — | 6379 | — | carts (with TTL) and the product read cache, password protected |
| frontend | 8084 | 80 | none | the storefront page + a proxy to the four HTTP services |
| kafka | 29092 | 9092 | — | single broker, KRaft mode (no ZooKeeper) |

## Run

```bash
cp .env.example .env          # once, then edit the passwords if you like
docker compose up --build
```

First start takes a few minutes: the image builds run Maven inside the container, so **no local JDK is required**.

Check that it is up:

```bash
curl http://localhost:8080/actuator/health
curl http://localhost:8081/actuator/health
curl http://localhost:8082/actuator/health
curl http://localhost:8083/actuator/health
```

or simply open <http://localhost:8084>.

Stop (keep the data):

```bash
docker compose down
```

Stop and wipe the databases, the Kafka log and the carts:

```bash
docker compose down -v
```

## The storefront

`frontend/` is one HTML page, one stylesheet, one script — no build step, no npm, no framework:

| View | What it shows |
|---|---|
| Store | the catalogue from search-service, with the search box, category filter and price window |
| Cart | the cart from cart-service, quantities editable, checkout, and what happened to the order |
| Orders | one order by id, its status and its lines, live while it is `PENDING` |

The page is served by nginx, which also forwards `/api/products`, `/api/orders`, `/api/carts` and
`/api/search` to the service that owns each prefix. **The browser therefore only talks to one origin**,
so not a single service needs a CORS rule, and the page sees exactly the same URLs it will see when
api-gateway takes this job over in Step 5.

The interesting part for the architecture: the cart stores product ids only, so the cart view asks
product-service for each name and price as it renders. That is the same read model an e-commerce site
has — a cart is a list of references, not a copy of the catalogue.

![The cart](docs/screenshots/cart.png)

![One order](docs/screenshots/orders.png)

## The order flow

```
client ──POST /orders──> order-service
                             │  GET /products/{id} (HTTP, for the price)
                             ▼
                        product-service
                             │
   order-service saves the order as PENDING
                             │
              ┌──────────────┴──────────────┐
              │  order-events (key=orderId) │
              └──────────────┬──────────────┘
                             ▼
                     product-service
              reserves stock in one transaction
              (idempotent, see below)
                             │
             ┌───────────────┴────────────────┐
             │ inventory-events (key=orderId) │
             └───────────────┬────────────────┘
                 ┌───────────┴───────────┐
                 ▼                       ▼
           order-service          notification-service
     CONFIRMED / REJECTED            simulated e-mail
```

`POST /orders` therefore answers **before** the stock question is settled: it returns `PENDING`.
`GET /orders/{id}` a moment later returns `CONFIRMED` (stock was reserved) or `REJECTED`
(the product is unknown or there is not enough stock).

### Topics

| Topic | Key | Partitions | Events | Produced by | Consumed by |
|---|---|---|---|---|---|
| `order-events` | orderId | 3 | `OrderPlaced`, `OrderConfirmed`, `OrderRejected` | order-service | product-service, notification-service |
| `inventory-events` | orderId | 3 | `StockReserved`, `StockRejected` | product-service | order-service, notification-service |
| `product-events` | productId | 3 | `ProductCreated`, `ProductUpdated`, `ProductDeleted` | product-service | search-service |

The topics are declared in code (`KafkaTopicConfig` with `TopicBuilder`) and the broker runs with
`KAFKA_AUTO_CREATE_TOPICS_ENABLE=false`, so the partition count is always the one we chose rather than
the broker default of one.

One topic carries three record types, so the topic name alone does not say what a consumer was given:
the JSON `__TypeId__` header decides which of the three records the deserializer builds, and every
listener switches on the value it receives. product-service acts on `OrderPlaced` and ignores the two
answers that it produced itself; notification-service remembers `OrderPlaced` and writes the e-mail
when `OrderConfirmed` or `OrderRejected` arrives. All three events of one order share the order id as
key, so they land on the same partition and are consumed in the order they happened — the mail always
knows the content of the order before its status.

## product-service — /products

```bash
# create
curl -X POST http://localhost:8080/products -H "Content-Type: application/json" -d '{
  "name": "Mechanical keyboard",
  "description": "75% layout, brown switches",
  "category": "peripherals",
  "price": 89.90,
  "stock": 25
}'

# list / read
curl http://localhost:8080/products
curl http://localhost:8080/products/1

# update
curl -X PUT http://localhost:8080/products/1 -H "Content-Type: application/json" -d '{
  "name": "Mechanical keyboard",
  "description": "75% layout, brown switches",
  "category": "peripherals",
  "price": 79.90,
  "stock": 30
}'

# delete
curl -X DELETE http://localhost:8080/products/1
```

## search-service — /search

product-service publishes `ProductCreated`, `ProductUpdated` and `ProductDeleted` on `product-events`
(key = productId) after every write, and search-service consumes them into the `products` index. Nothing
reads product-service's database: the index is built purely from the event stream.

The mapping is declared explicitly instead of being guessed, because the field type decides which queries
work: `name` and `description` are `text` (analysed, full-text), `category` is `keyword` (exact filter),
`price` is `double` and `stock` an `integer` (range filters).

```bash
# everything (default page size 10)
curl "http://localhost:8082/search"

# full text over name and description
curl "http://localhost:8082/search?q=keyboard"

# only one category, only a price window, page 0, 5 per page
curl "http://localhost:8082/search?category=peripherals&minPrice=50&maxPrice=100&page=0&size=5"
```

```json
{
  "total": 1,
  "page": 0,
  "size": 10,
  "items": [
    { "id": 4, "name": "Mechanical keyboard", "description": "75% layout with brown switches",
      "category": "peripherals", "price": 89.9, "stock": 25 }
  ]
}
```

All filters are optional and combine: `q` matches name **or** description, `category` is an exact term,
`minPrice`/`maxPrice` bound the price. `page` starts at 0, `size` is capped at 100, and a nonsense request
(`size=0`, `minPrice > maxPrice`) answers `400` with a problem+json body.

## order-service — /orders

`POST /orders` takes a list of `productId` + `quantity`. The prices are **not** sent by the client:
order-service asks product-service over HTTP for each price and computes the total.

```bash
curl -X POST http://localhost:8081/orders -H "Content-Type: application/json" -d '{
  "items": [
    { "productId": 1, "quantity": 2 },
    { "productId": 2, "quantity": 1 }
  ]
}'

curl http://localhost:8081/orders/1
```

Response of the POST (the GET looks the same, but with the settled status):

```json
{
  "id": 1,
  "status": "PENDING",
  "totalPrice": 259.70,
  "createdAt": "2026-11-04T18:00:00Z",
  "items": [
    { "productId": 1, "quantity": 2, "unitPrice": 89.90 },
    { "productId": 2, "quantity": 1, "unitPrice": 79.90 }
  ]
}
```

## cart-service — /carts/{userId}

A cart is one Redis hash at `carts:{userId}` (`@RedisHash("carts")` + `CrudRepository`, so the key is
derived from the user id, not from a database sequence). Prices are **not** stored in the cart: they are
resolved by order-service when the cart is checked out, exactly as for a directly posted order.

```bash
# read (an unknown user is an empty cart, not a 404)
curl http://localhost:8083/carts/alice

# add 2 x product 4 (adding the same product again increases the quantity)
curl -X POST http://localhost:8083/carts/alice/items -H "Content-Type: application/json" -d '{"productId": 4, "quantity": 2}'

# set an absolute quantity
curl -X PUT http://localhost:8083/carts/alice/items/4 -H "Content-Type: application/json" -d '{"quantity": 5}'

# remove one line, or empty the whole cart
curl -X DELETE http://localhost:8083/carts/alice/items/4
curl -X DELETE http://localhost:8083/carts/alice

# turn the cart into an order
curl -X POST http://localhost:8083/carts/alice/checkout
```

```json
{ "userId": "alice", "items": [ { "productId": 4, "quantity": 2 } ], "totalQuantity": 2 }
```

### Expiry

`Cart` carries `@TimeToLive(unit = SECONDS)`, so every write also writes the TTL of the hash:

> **A cart expires 7 days after the last modification** (`Cart.TTL_SECONDS = 7 * 24 * 60 * 60`).
> Adding, changing or removing an item resets the clock, because a live cart is not an abandoned one.

```bash
docker compose exec redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning TTL carts:alice
# 604800  (and after a week of silence the key is simply gone)
```

The values are stored as JSON, not as Java serialization, so the content of a cart can be read by hand:

```bash
docker compose exec redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning HGETALL carts:alice
```

Redis runs with AOF on a named volume, so a restart of the container keeps the carts (and their TTLs);
`docker compose down -v` is what really throws them away.

### Checkout never loses a cart

`POST /carts/{userId}/checkout` posts the items to order-service and then waits for the order to leave
`PENDING` (up to `CHECKOUT_TIMEOUT_MS`, polling every `CHECKOUT_POLL_INTERVAL_MS`):

```json
{ "orderId": 4, "orderStatus": "CONFIRMED", "cartCleared": true, "message": "Order accepted, cart cleared." }
```

**The cart is deleted only after a `CONFIRMED`.** A `REJECTED` order keeps the cart untouched
(`cartCleared: false`) together with its 502/200 answer, so the customer can fix the quantity and try
again instead of losing the basket to an out-of-stock product. A cart that is still empty after the
timeout is also kept.

## Caching in product-service

`GET /products/{id}` is `@Cacheable("products")` through Redis (10 minute TTL, JSON values, nulls never
cached), because it is read far more often than written — order pricing and cart checkout hit it on every
request.

The cache is evicted `@CacheEvict` on every path that can change what the endpoint returns:

| Change | Where |
|---|---|
| `PUT /products/{id}` | `ProductController.update` |
| `DELETE /products/{id}` | `ProductController.delete` |
| stock reserved by an order | `OrderEventListener` via `ProductCache.evict` |

The eviction from the Kafka listener goes through a small `ProductCache` bean instead of a call inside
`OrderEventListener`: Spring's cache annotations are applied by a proxy, so a call from one method of a
class to another method of the same class would silently skip them.

```bash
curl http://localhost:8080/products/4
docker compose exec redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning KEYS 'products*'
# products::4      (TTL 600)
curl -X PUT http://localhost:8080/products/4 ...   # the key disappears
```

## Watching the events

```bash
# every event on both topics
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic order-events --from-beginning \
  --property print.key=true --property print.value=true

# partition count of the three topics
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --describe
```

The notification-service log is where the "e-mails" appear:

```bash
docker compose logs -f notification-service
```

```
================ SIMULATED EMAIL ================
To      : customer of order #1
Subject : Your ShopStream order was confirmed
Total   : 259.70
Items   :
          - 2 x product 1
          - 1 x product 2
=================================================
```

## Why the stock step cannot run twice

Kafka guarantees *at least once* delivery: a rebalance, a restart or a retried record can hand the
same `OrderPlaced` to product-service twice. Decrementing stock twice would be a silent bug that only
shows up as an inventory that does not match reality.

`InventoryService.reserve()` therefore works inside a single database transaction:

1. if `processed_orders` already has a row for this `orderId`, return the stored outcome and touch nothing;
2. otherwise check every line, reject the whole order if any product is unknown or short on stock;
3. decrement the stock, insert the `processed_orders` row, commit, and only then publish the result.

Replaying an event by hand needs the `__TypeId__` header as well: a plain JSON line sent without it
gives the consumer no class to deserialize into. The replay that proved this behaviour is recorded in
`NOTES.md`, section 4.4.

## Configuration

Every connection setting is an environment variable. Nothing points to `localhost` inside a container —
service-to-service URLs use the compose service names.

| Variable | Used by | Default in compose |
|---|---|---|
| `DB_URL` | product-service, order-service | `jdbc:mysql://mysql-product:3306/products` / `...mysql-order:3306/orders` |
| `DB_USER` | product-service, order-service | `${MYSQL_USER}` |
| `DB_PASSWORD` | product-service, order-service | `${MYSQL_PASSWORD}` |
| `PRODUCT_SERVICE_URL` | order-service | `http://product-service:8080` |
| `ORDER_SERVICE_URL` | cart-service | `http://order-service:8080` |
| `REDIS_HOST` / `REDIS_PORT` | product-service, cart-service | `redis` / `6379` |
| `REDIS_PASSWORD` | product-service, cart-service, redis | `${REDIS_PASSWORD}` from `.env` |
| `CHECKOUT_TIMEOUT_MS` / `CHECKOUT_POLL_INTERVAL_MS` | cart-service | `5000` / `250` |
| `KAFKA_BOOTSTRAP_SERVERS` | all three services | `kafka:9092` |
| `ELASTICSEARCH_URIS` | search-service | `http://elasticsearch:9200` |
| `SERVER_PORT` | product-service, order-service, search-service, cart-service | `8080` |

The compose file itself reads `.env` (`MYSQL_ROOT_PASSWORD`, `MYSQL_USER`, `MYSQL_PASSWORD`,
`PRODUCT_DB_NAME`, `ORDER_DB_NAME`, `REDIS_PASSWORD`). `.env` is git-ignored; `.env.example` is the template.

## Layout

```
shopstream/
├── docker-compose.yml
├── .env.example
├── product-service/      product CRUD + stock reservation
├── order-service/        orders + saga state machine
├── cart-service/         carts in Redis, checkout into an order
├── frontend/             the storefront page + its proxy
├── notification-service/ simulated e-mails
├── search-service/       product index + /search
└── events/               (per service) the shared event contract package
```

Each service is a self-contained Maven project with its own `Dockerfile`, and each carries its own copy
of the `hu.unimiskolc.shopstream.events` package. The copies are identical on purpose: services must be
independently buildable and deployable, and the JSON type header (`__TypeId__`) written by the producer
is the *class name*, so the class has to exist under the same name on the consumer side.

## Roadmap

- [x] Step 1 — Docker: two services, two MySQL databases, one `docker compose up`
- [x] Step 2 — Kafka: order-events / inventory-events / product-events, async confirmation
- [x] Step 3 — Elasticsearch: search-service, `products` index, full-text + filters
- [x] Step 4 — Redis: cart-service with TTL, product cache
- [ ] Step 5 — Spring Cloud: Eureka, config server, Feign, gateway