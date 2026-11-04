# ShopStream

Distributed e-commerce platform for the *Development of Distributed Web Applications* semester project.

**Current state: Step 1 — Docker.** Two Spring Boot services, each with its own MySQL, started with one command.

## Services

| Service | Host port | Container port | Database |
|---|---|---|---|
| product-service | 8080 | 8080 | `products` (mysql-product) |
| order-service   | 8081 | 8080 | `orders`   (mysql-order)   |

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

Stop and wipe the databases:

```bash
docker compose down -v
```

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

Response:

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

The status is `PENDING` on purpose: Step 2 replaces this with the Kafka flow
(`OrderPlaced` → `StockReserved` → `CONFIRMED`).

## Configuration

Every connection setting is an environment variable. Nothing points to `localhost` inside a container —
service-to-service URLs use the compose service names.

| Variable | Used by | Default in compose |
|---|---|---|
| `DB_URL` | both services | `jdbc:mysql://mysql-product:3306/products` / `...mysql-order:3306/orders` |
| `DB_USER` | both services | `${MYSQL_USER}` |
| `DB_PASSWORD` | both services | `${MYSQL_PASSWORD}` |
| `PRODUCT_SERVICE_URL` | order-service | `http://product-service:8080` |
| `SERVER_PORT` | both services | `8080` |

The compose file itself reads `.env` (`MYSQL_ROOT_PASSWORD`, `MYSQL_USER`, `MYSQL_PASSWORD`,
`PRODUCT_DB_NAME`, `ORDER_DB_NAME`). `.env` is git-ignored; `.env.example` is the template.

## Layout

```
shopstream/
├── compose.yaml
├── .env.example
├── product-service/
│   ├── Dockerfile
│   ├── pom.xml
│   └── src/main/java/hu/unimiskolc/shopstream/product/
└── order-service/
    ├── Dockerfile
    ├── pom.xml
    └── src/main/java/hu/unimiskolc/shopstream/order/
```

## Roadmap

- [x] Step 1 — Docker: two services, two MySQL databases, one `docker compose up`
- [ ] Step 2 — Kafka: order-events / inventory-events / product-events, async confirmation
- [ ] Step 3 — Elasticsearch: search-service, products index
- [ ] Step 4 — Redis: cart-service, product cache
- [ ] Step 5 — Spring Cloud: Eureka, config server, Feign, gateway
