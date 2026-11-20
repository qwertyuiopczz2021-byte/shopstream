
# -*- coding: utf-8 -*-
from reportlab.lib.units import cm


def chapter8(b):
    b.h1("8  Testing and verification")
    b.h2("8.1  How the system was checked")
    b.p("There is no unit test suite in this repository, and the report should not pretend "
        "otherwise. What the project does have is a set of recorded end-to-end checks: every claim "
        "in the previous five chapters is backed by a command that was run against the running "
        "system through the gateway, and by its actual output, captured as a terminal transcript "
        "and reproduced as a figure. That choice follows the assignment, which asks for evidence of "
        "the running system rather than for coverage numbers, and it forced the checks to go "
        "through the same surface a client uses - the gateway on port 8080 - instead of calling a "
        "service on a port that is not published.")
    b.p("Two rules were applied consistently. First, nothing is verified through the containers' "
        "internal ports; if a check cannot be made through the gateway, it is not a property of the "
        "system the user sees. The exceptions are the places where the evidence is by definition "
        "internal - the Kafka topics, the Redis hash, the service logs - and those are read with "
        "<font name='Consola' size='9'>docker exec</font> and "
        "<font name='Consola' size='9'>docker logs</font>, never by weakening the compose file. "
        "Second, every check states what was expected before it states what happened, so a reader "
        "can tell a passing check from a check that was written to match its result.")

    b.h2("8.2  The checks")
    b.table(
        ["Check", "How it was exercised", "Result"],
        [
            ["Catalogue CRUD", "POST, GET, PUT and GET /api/products through the gateway",
             "201 / 200 / 200 with the new price; the list contains the product"],
            ["Full-text search", "GET /api/search?q=brown - a word that appears only in description",
             "one hit, the mechanical keyboard"],
            ["Filtered search", "?category=accessories&amp;minPrice=30&amp;maxPrice=80", "total 3, all three accessories in range"],
            ["Pagination", "?q=usb&amp;size=2", "two hits per page, total 2"],
            ["Invalid range", "?minPrice=200&amp;maxPrice=100", "400 with a ProblemDetail explaining the constraint"],
            ["Empty result", "?category=audio", "200 with total 0, not an error"],
            ["Order happy path", "POST /api/orders, then GET the order", "PENDING, then CONFIRMED about a second later"],
            ["Stock rejection", "cart with 5 of a product that has 2, then checkout", "order REJECTED, product stock still 2, cart kept"],
            ["Notification", "docker logs of notification-service", "exactly one e-mail per order, for both outcomes"],
            ["Cart and TTL", "HGETALL and TTL on carts:guest", "hash with the class field, TTL 604800 seconds"],
            ["Cart cleared on success", "checkout of a well-stocked cart", "cartCleared true and the key removed"],
            ["Index follows the catalogue", "PUT and DELETE, then search again", "new price and new stock visible, deleted product gone"],
            ["Request id", "GET /api/products with -Headers", "the response carries X-Request-Id"],
            ["Route table", "GET /actuator/gateway/routes", "five routes, four of them lb://"],
            ["Instance failure", "stop product-service, keep requesting, start it again",
             "mixed 500/200 while the lease expires, then all 200"],
            ["Cold start", "immediate request after docker compose up", "503 for about 35 seconds, then 200"],
        ],
        [3.5, 7.0, 5.9], "The verification matrix. Every row corresponds to a recorded transcript, "
        "several of which appear as figures in this report.")

    b.h2("8.3  The walk-through that ties it together")
    b.p("The single most convincing check is one order followed from beginning to end, because it "
        "crosses all five steps. The sequence is: a product is created through the gateway, "
        "product-service writes it and publishes ProductCreated, search-service indexes it, a "
        "search finds it, it is added to a cart in Redis, the cart is checked out, cart-service "
        "places an order and waits, order-service stores PENDING and publishes OrderPlaced, "
        "product-service reserves the stock and publishes StockReserved, order-service confirms, "
        "notification-service writes the e-mail, cart-service sees CONFIRMED and clears the cart, "
        "and the next search shows the reduced stock.")
    b.p("Five services, two databases, one index, one cache and three topics take part, and no "
        "service reads another service's storage. The figures in this report are the checkpoints "
        "along that path: Figure 5 the containers, Figure 7 the topics, Figure 8 the two events of "
        "one order, Figure 9 the order moving from PENDING to CONFIRMED, Figure 10 the e-mail, "
        "Figure 12 the cart in Redis and Figure 13 the checkout.")

    b.h2("8.4  The rejection path")
    b.p("The confirmed path is the easy one. The rejection path is where the design is tested, "
        "because three services have to agree that nothing happened. A product was created with a "
        "stock of two, five of it were put in the cart, and the checkout was run:")
    b.fig("fig-rejection.png", "Checkout of five units of a product with a stock of two. The order is "
          "REJECTED, the product still has a stock of two, and the cart still holds the five units.")
    b.p("Three things are visible in that transcript and each of them is a requirement. The order "
        "status is REJECTED rather than an error, so the saga terminated properly instead of "
        "throwing. The product still shows <font name='Consola' size='9'>stock: 2</font>, which is "
        "the proof that the reservation is all-or-nothing: the four units that would not fit were "
        "never subtracted. And the cart still contains the five units with "
        "<font name='Consola' size='9'>cartCleared: false</font>, which is the Step 4 requirement "
        "that a failed checkout must not lose the basket.")
    b.p("The reason is carried all the way to the customer-facing message. product-service puts it "
        "in the InventoryEvent, order-service stores the status, and notification-service writes it "
        "into the e-mail:")
    b.fig("fig-rejected-email.png", "The notification of the rejected order, with the reason that "
          "product-service produced.")

    b.h2("8.5  Deliberate failure")
    b.p("Stopping one of the two product-service instances while the storefront is in use tests the "
        "load balancer, the registry and the gateway at once. The result is shown in Figure 17: the "
        "first requests after the stop alternate between 200 and 500, because the gateway is still "
        "round-robining over two addresses and one of them is dead. Once the Eureka lease expires - "
        "about ninety seconds with the settings in this project - the dead instance leaves the "
        "registry and every request succeeds again. Starting the instance back returns the system "
        "to its original state without any manual intervention.")
    b.p("A cold start is the other failure mode that a demo will hit. When the whole stack is "
        "brought up, the gateway answers 503 for roughly thirty-five seconds, because it has no "
        "instances to route to until the services have registered. The response is a proper "
        "ProblemDetail - <font name='Consola' size='9'>\"status\":503,\"error\":\"Service "
        "Unavailable\",\"requestId\":\"...\"</font> - rather than a connection reset, which is the "
        "behaviour a client library can retry on.")

    b.h2("8.6  What was not covered")
    b.p("Saying what is missing is part of the report. There are no automated tests: no JUnit for "
        "the services, no Testcontainers, no contract test between the event producers and "
        "consumers, and therefore no regression safety net for future changes. The idempotency "
        "guard in InventoryService was verified by reading the code and the table, not by injecting "
        "a duplicate message; a proper test would use a consumer that seeks back and replays one "
        "record. The Redis cache was not measured - no hit ratio, no timing comparison with the "
        "cache disabled - so the claim that it helps is a design argument, not a measurement. There "
        "is no load test: the system was exercised by one client at a time, and the two "
        "product-service instances were shown to share traffic, not to sustain it. And there is no "
        "security testing, because there is no security to test; Section 9.7 explains why that is a "
        "deliberate scope decision rather than an oversight.")


def chapter9(b):
    b.h1("9  Discussion")
    b.p("This chapter is the honest part of the report: what broke, what is a compromise, and what "
        "would have to change before the system could be used by anyone but its author.")

    b.h2("9.1  A version skew that no amount of reading the code would reveal")
    b.p("The api-gateway failed to start with <font name='Consola' size='9'>NoSuchMethodError: "
        "'java.util.Set org.springframework.http.HttpHeaders.headerSet()'</font>, thrown from inside "
        "Spring Cloud Gateway's own <font name='Consola' size='9'>RemoveHopByHopHeadersFilter</font>. "
        "The stack trace points at a line that exists in the library, so the library was not the "
        "problem; the method it calls was added to Spring Framework in 6.1.21, and Spring Boot 3.3.4 "
        "manages 6.1.13.")
    b.p("The fix was to move the whole build to Boot 3.3.13, which manages Framework 6.1.21. Two "
        "lessons are worth keeping. First, in a multi-module Maven project the parent version is a "
        "project-wide decision: eight modules had to be upgraded together, and pinning only the "
        "gateway would have produced a build where the same class had two versions depending on "
        "which module you asked. Second, a <font name='Consola' size='9'>NoSuchMethodError</font> "
        "at runtime is always a version conflict, never a coding mistake, and the useful question is "
        "not <i>why is this method missing</i> but <i>which BOM should have provided it</i>.")

    b.h2("9.2  AFTER_COMMIT is not an outbox")
    b.p("Publishing domain events from a transaction-bound listener fixed the failure that matters "
        "in practice - a rolled-back order no longer announces itself - but it does not make the "
        "database and the log atomic. If the process dies between the commit and the "
        "<font name='Consola' size='9'>kafkaTemplate.send</font>, the order exists and no event was "
        "ever produced; the saga never starts and the order stays PENDING forever.")
    b.p("The textbook fix is a transactional outbox: write the event into a table in the same "
        "transaction, let a poller read the table and publish, and delete or mark the row when the "
        "broker acknowledged it. That is a table, a scheduled job and an idempotent publisher - "
        "roughly a day of work - and it is the first thing I would add with more time, together with "
        "a reconciliation job that finds orders that have been PENDING for longer than a minute. The "
        "current design is defensible for a project whose events are all derived from data that "
        "still exists in a table, but the gap should be named rather than hidden.")

    b.h2("9.3  Consistency of the read model")
    b.p("The Elasticsearch index is eventually consistent with the catalogue, and the delay is "
        "normally milliseconds but is not bounded. A product created through the API can therefore "
        "be missing from a search for a moment. The same is true of the stock field: it is refreshed "
        "by a ProductUpdated event after a reservation, so a shopper can briefly see a quantity that "
        "has just been sold.")
    b.p("This is the right trade for a catalogue, which is read far more often than it is written, "
        "but it has to be a stated property rather than an accident. The mitigation that is already "
        "in place is that the index is rebuildable: the consumer starts at "
        "<font name='Consola' size='9'>earliest</font> and the topics hold the history, so deleting "
        "the index and restarting search-service reconstructs it from the event log. That is the "
        "property that makes a derived store acceptable in the first place.")

    b.h2("9.4  State in memory is state that disappears")
    b.p("notification-service keeps the placed-order payloads and the set of already-notified order "
        "ids in a <font name='Consola' size='9'>ConcurrentHashMap</font>. It is the simplest thing "
        "that satisfies the requirement of one e-mail per order, but it has two consequences. A "
        "restart loses the set, so a redelivered event after a restart can produce a second e-mail "
        "for the same order. And the service can only run as a single instance: a second replica "
        "would have its own map and its own consumer group member, and the two would disagree about "
        "what has been sent.")
    b.p("The fix is the same shape as the idempotency table in product-service - a small table of "
        "sent notifications keyed by order id - which would also make the service horizontally "
        "scalable. It was not done because the assignment explicitly asks for a log line rather than "
        "a database write, and adding a fourth database to the compose file for one table felt like "
        "the wrong kind of completeness. It is documented because the next reader will otherwise "
        "assume the notification service is safe to scale.")

    b.h2("9.5  One broker, one partition copy")
    b.p("Kafka runs as a single broker with replication factor one, which means the event log is "
        "exactly as durable as the container's disk and no more. A broker failure stops the saga "
        "rather than degrading it. The three-partition, one-replica setting is visible in the topic "
        "configuration and is the honest setting for a single machine: a replication factor of two "
        "on one broker is rejected by Kafka, and a replication factor of three would need three "
        "brokers and about a gigabyte of memory that the laptop does not have to spare while "
        "Elasticsearch, MySQL twice, Redis and eight JVMs are also running.")
    b.p("What would change in a real deployment is not only the replication factor but the topics' "
        "retention: the defaults keep seven days, which is fine for a demo and would be a capacity "
        "decision for a catalogue whose events are used to rebuild an index.")

    b.h2("9.6  Schema management")
    b.p("Both databases are created with <font name='Consola' size='9'>ddl-auto: update</font>. It "
        "is convenient - a new field appears in the table on the next start - and it is exactly what "
        "a production system must not do, because it can never drop a column, never rename one "
        "safely, and gives no record of what changed when. Flyway with one migration per step would "
        "have cost perhaps an hour and would have made the database schema a reviewable artifact, "
        "which is also what a reader of this report would want to see. The choice is recorded here "
        "as a known shortcut, together with the observation that the schema is small enough - two "
        "tables in each database - that it has not caused a problem yet.")

    b.h2("9.7  There is no authentication")
    b.p("The cart API takes the user id from the path, and nothing checks that the caller is that "
        "user. Anyone who can reach port 8080 can read, modify, check out and clear the cart of "
        "anybody. The same is true of the order API: any caller can read any order by id.")
    b.p("This is a scope decision, and the assignment is explicit that authentication is not part "
        "of it - the five steps are about distribution, messaging, search, caching and cloud "
        "infrastructure. Adding it would have meant a token issuer, a filter on the gateway and a "
        "decision about how the identity travels to the services, which is a project of its own. The "
        "decision is stated here rather than left implicit because a reader who finds the cart of "
        "<i>guest</i> in the URL might reasonably conclude that security was forgotten; it was "
        "postponed deliberately, and the gateway is the place where it would be added, since it is "
        "already the only published port.")

    b.h2("9.8  What I would do with another month")
    b.p("In order: an outbox plus a reconciliation job for orders stuck in PENDING (9.2); "
        "Testcontainers-based integration tests for the saga, including an explicit duplicate "
        "delivery (8.6); a persisted notification log so that service can scale (9.4); Flyway "
        "migrations (9.6); and authentication at the gateway (9.7). After that the system would be "
        "ready for the two things this report cannot show - a load test with concurrent checkouts, "
        "and a chaos experiment that kills a broker during a saga instead of only stopping a "
        "product-service instance.")


def chapter10(b):
    b.h1("10  Conclusion")
    b.p("The project set out to build a distributed e-commerce platform in five increments, and the "
        "result is fifteen containers that start with one command and behave like a system rather "
        "than like five demos. The catalogue is a service with its own database; ordering is a saga "
        "over three Kafka topics with a one-way state machine and an idempotent reservation; search "
        "is a derived index that is rebuilt from events and never read from another service's "
        "tables; the cart lives in Redis with a TTL and is cleared only when the order it produced "
        "is actually accepted; and everything is registered, configured and reachable through a "
        "single published port.")
    b.p("What the five steps actually taught is that the hard part is never the happy path. Writing "
        "a CRUD endpoint took an afternoon; deciding what happens when the stock is insufficient, "
        "when a message arrives twice, when the cache holds a price that has changed, when an "
        "instance dies while a request is in flight, or when a container starts before the registry "
        "knows about it - that is where the design lives. Each of those cases is answered somewhere "
        "in this report by a specific mechanism: the processed_orders table, the "
        "<font name='Consola' size='9'>AFTER_COMMIT</font> listener, the "
        "<font name='Consola' size='9'>@CacheEvict</font> that the inventory listener calls, the "
        "load-balanced <font name='Consola' size='9'>lb://</font> route with its registry lease, and "
        "the ProblemDetail that a 503 returns.")
    b.p("The system also knows what it is not. It has no automated tests, no outbox, no "
        "authentication and a single Kafka broker; the notification service cannot be scaled and the "
        "schema is managed by Hibernate guessing. Those are listed in Chapter 9 as open work rather "
        "than hidden, because a distributed system is defined as much by the failures it admits as "
        "by the features it lists. Given another month, the next commit would be the outbox, and the "
        "one after that the tests that prove it works when a message arrives twice.")


def appendices(b):
    b.h1("Appendix A  The HTTP API")
    b.p("Everything below is reachable on <font name='Consola' size='9'>http://localhost:8080</font> "
        "and nothing else is published. The service column names the container that actually handles "
        "the request after the gateway has stripped the <font name='Consola' size='9'>/api</font> "
        "prefix.")
    b.table(
        ["Method and path", "Service", "Purpose"],
        [
            ["GET /api/products", "product-service", "List the catalogue"],
            ["GET /api/products/{id}", "product-service", "One product, cached in Redis"],
            ["POST /api/products", "product-service", "Create; publishes ProductCreated"],
            ["PUT /api/products/{id}", "product-service", "Update; evicts the cache, publishes ProductUpdated"],
            ["DELETE /api/products/{id}", "product-service", "Delete; publishes ProductDeleted"],
            ["POST /api/orders", "order-service", "Place an order; answers PENDING"],
            ["GET /api/orders/{id}", "order-service", "Order with status and lines"],
            ["GET /api/carts/{userId}", "cart-service", "The cart of a user"],
            ["POST /api/carts/{userId}/items", "cart-service", "Add a product"],
            ["PUT /api/carts/{userId}/items/{productId}", "cart-service", "Change a quantity"],
            ["DELETE /api/carts/{userId}/items/{productId}", "cart-service", "Remove a line"],
            ["DELETE /api/carts/{userId}", "cart-service", "Empty the cart"],
            ["POST /api/carts/{userId}/checkout", "cart-service", "Place an order from the cart"],
            ["GET /api/search", "search-service", "q, category, minPrice, maxPrice, page, size"],
        ],
        [6.4, 3.4, 6.6], "The public API as seen from port 8080. The actuators are not routed: "
        "they are reachable on each service's own port, inside the compose network only.")

    b.h1("Appendix B  Configuration reference")
    b.p("Every value below is an environment variable with a default in "
        "<font name='Consola' size='9'>config-repo</font>, so the same images run unchanged in a "
        "different environment.")
    b.table(
        ["Variable", "Used by", "Meaning"],
        [
            ["DB_URL", "product, order", "JDBC URL, pointing at mysql-product or mysql-order"],
            ["DB_USER / DB_PASSWORD", "product, order", "Database credentials"],
            ["KAFKA_BOOTSTRAP_SERVERS", "four services", "kafka:9092 in compose"],
            ["REDIS_HOST / REDIS_PORT / REDIS_PASSWORD", "product, cart", "The shared Redis, which has a password"],
            ["ELASTICSEARCH_URIS", "search", "http://elasticsearch:9200"],
            ["EUREKA_DEFAULT_ZONE", "every service", "http://discovery-server:8761/eureka/"],
            ["CHECKOUT_TIMEOUT_MS", "cart", "How long checkout waits for a decision (5000)"],
            ["CHECKOUT_POLL_INTERVAL_MS", "cart", "How often it asks (250)"],
            ["shopstream.topics.*", "producers, consumers", "Topic names and partition counts"],
        ],
        [6.0, 3.6, 6.8], "The bootstrap environment. Everything else comes from config-server.")

    b.h1("Appendix C  Running the system")
    b.p("From the repository root, with Docker running:")
    b.p("<font name='Consola' size='9'>docker compose up -d --build</font> starts everything. The "
        "storefront is at <font name='Consola' size='9'>http://localhost:8080</font>; the first "
        "thirty-five seconds return 503 while the services register. "
        "<font name='Consola' size='9'>docker compose --profile dev up -d</font> additionally "
        "publishes the Eureka dashboard on 8761 and the Kafka listener on 9092. "
        "<font name='Consola' size='9'>docker compose down</font> stops the system and keeps the "
        "data; <font name='Consola' size='9'>docker compose down -v</font> also removes the volumes "
        "and the event log.")
    b.p("The report itself is generated by <font name='Consola' size='9'>python "
        "docs/report/build.py</font>, which reads the sources of this repository directly - every "
        "code listing in the report is extracted from the file at the line numbers stated in the "
        "caption, so the report cannot drift from the code it describes without the build failing.")

    b.h1("References")
    b.p("Spring Boot reference documentation, 3.3.x. <font size='9' color='#555555'>"
        "https://docs.spring.io/spring-boot/docs/3.3.x/reference/html/</font>")
    b.p("Spring Cloud Gateway reference, 4.1.x. <font size='9' color='#555555'>"
        "https://docs.spring.io/spring-cloud-gateway/reference/</font>")
    b.p("Spring for Apache Kafka reference, 3.2.x - transactions, listener acknowledgement and "
        "error handling. <font size='9' color='#555555'>"
        "https://docs.spring.io/spring-kafka/reference/</font>")
    b.p("Spring Data Redis reference - <font name='Consola' size='9'>@RedisHash</font>, "
        "<font name='Consola' size='9'>@TimeToLive</font> and repositories. "
        "<font size='9' color='#555555'>https://docs.spring.io/spring-data/redis/reference/</font>")
    b.p("Spring Data Elasticsearch reference - <font name='Consola' size='9'>@Document</font>, "
        "<font name='Consola' size='9'>@Field</font> and "
        "<font name='Consola' size='9'>ElasticsearchOperations</font>. <font size='9' color='#555555'>"
        "https://docs.spring.io/spring-data/elasticsearch/reference/</font>")
    b.p("Apache Kafka documentation - topic configuration, consumer groups, delivery guarantees. "
        "<font size='9' color='#555555'>https://kafka.apache.org/documentation/</font>")
    b.p("Krizsán Zoltán, <i>Distributed Systems Development</i>, University of Miskolc, 2020 - the "
        "course textbook that the five lectures follow.")
    b.p("<i>Semester Project - Distributed E-Commerce Platform</i>, course handout, 2026.")
