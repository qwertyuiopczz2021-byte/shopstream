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
| Stack | Java 21, Spring Boot 3.3.4, MySQL 8.4, Docker Compose |

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

## 4. Roadmap

| Step | Topic | Status |
|---|---|---|
| 1 | Docker: product-service, order-service, two MySQL databases | done |
| 2 | Kafka (KRaft): order-events, inventory-events, product-events; saga + idempotent stock | planned |
| 3 | Elasticsearch: search-service, `products` index, full-text + filters | planned |
| 4 | Redis: cart-service, `@RedisHash`, TTL, checkout; product cache | planned |
| 5 | Spring Cloud: Eureka, Config Server, OpenFeign, Gateway, X-Request-Id | planned |
