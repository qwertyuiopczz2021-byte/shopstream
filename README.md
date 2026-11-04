# ShopStream

Distributed e-commerce platform for the *Development of Distributed Web Applications* semester project.

**Current state: Step 2 — Kafka.** Three Spring Boot services and a single KRaft Kafka broker.
Orders are confirmed or rejected asynchronously through events, and stock is decremented exactly once.

## Services

| Service | Host port | Container port | Database | Role |
|---|---|---|---|---|
| product-service | 8080 | 8080 | `products` (mysql-product) | product CRUD, reserves stock |
| order-service   | 8081 | 8080 | `orders` (mysql-order)     | places orders, tracks their state |
| notification-service | — | — | none | writes one simulated e-mail per finished order |
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
```

Stop (keep the data):

```bash
docker compose down
```

Stop and wipe the databases and the Kafka log:

```bash
docker compose down -v
```

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

| Topic | Key | Partitions | Produced by | Consumed by |
|---|---|---|---|---|
| `order-events` | orderId | 3 | order-service | product-service, notification-service |
| `inventory-events` | orderId | 3 | product-service | order-service, notification-service |
| `product-events` | productId | 3 | product-service | search-service (Step 3) |

The topics are declared in code (`KafkaTopicConfig` with `TopicBuilder`) and the broker runs with
`KAFKA_AUTO_CREATE_TOPICS_ENABLE=false`, so the partition count is always the one we chose rather than
the broker default of one.

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

Try it yourself — send the same event twice and watch the stock move once:

```bash
docker compose exec kafka kafka-console-producer --bootstrap-server localhost:9092 --topic order-events
```

## Configuration

Every connection setting is an environment variable. Nothing points to `localhost` inside a container —
service-to-service URLs use the compose service names.

| Variable | Used by | Default in compose |
|---|---|---|
| `DB_URL` | product-service, order-service | `jdbc:mysql://mysql-product:3306/products` / `...mysql-order:3306/orders` |
| `DB_USER` | product-service, order-service | `${MYSQL_USER}` |
| `DB_PASSWORD` | product-service, order-service | `${MYSQL_PASSWORD}` |
| `PRODUCT_SERVICE_URL` | order-service | `http://product-service:8080` |
| `KAFKA_BOOTSTRAP_SERVERS` | all three services | `kafka:9092` |
| `SERVER_PORT` | product-service, order-service | `8080` |

The compose file itself reads `.env` (`MYSQL_ROOT_PASSWORD`, `MYSQL_USER`, `MYSQL_PASSWORD`,
`PRODUCT_DB_NAME`, `ORDER_DB_NAME`). `.env` is git-ignored; `.env.example` is the template.

## Layout

```
shopstream/
├── compose.yaml
├── .env.example
├── product-service/      product CRUD + stock reservation
├── order-service/        orders + saga state machine
├── notification-service/ simulated e-mails
└── events/               (per service) the shared event contract package
```

Each service is a self-contained Maven project with its own `Dockerfile`, and each carries its own copy
of the `hu.unimiskolc.shopstream.events` package. The copies are identical on purpose: services must be
independently buildable and deployable, and the JSON type header (`__TypeId__`) written by the producer
is the *class name*, so the class has to exist under the same name on the consumer side.

## Roadmap

- [x] Step 1 — Docker: two services, two MySQL databases, one `docker compose up`
- [x] Step 2 — Kafka: order-events / inventory-events / product-events, async confirmation
- [ ] Step 3 — Elasticsearch: search-service, products index
- [ ] Step 4 — Redis: cart-service, product cache
- [ ] Step 5 — Spring Cloud: Eureka, config server, Feign, gateway
