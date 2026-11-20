
# -*- coding: utf-8 -*-
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer


def chapter3(b):
    b.h1("3  Step 1 - Two services in containers")
    b.h2("3.1  What the step asked for")
    b.p("Step 1 asks for the smallest system that already has the shape of the final one. "
        "product-service must offer the full CRUD of a product plus a list, with the fields "
        "<font name='Consola' size='9'>id, name, description, category, price, stock</font>. "
        "order-service must accept <font name='Consola' size='9'>POST /orders</font> with a list of "
        "productId and quantity, and answer <font name='Consola' size='9'>GET /orders/{id}</font>, "
        "and it has to obtain the price of each product from product-service over HTTP rather "
        "than from its own tables. Both services need a Dockerfile, both need their own MySQL "
        "container with a named volume, and the whole thing has to start with one "
        "<font name='Consola' size='9'>docker compose up</font>. No connection string may point "
        "at localhost, and every connection detail has to come from an environment variable.")
    b.p("The last two requirements are the instructive ones, because they are not about Spring at "
        "all. A container has its own network namespace, so <font name='Consola' size='9'>localhost"
        "</font> inside the product-service container is the product-service container. Reaching "
        "MySQL means using the compose service name, which Docker's embedded DNS resolves on the "
        "shared network. The same reasoning applies to the URL order-service uses for "
        "product-service: in Step 1 it was an environment variable pointing at "
        "<font name='Consola' size='9'>http://product-service:8080</font>, and Step 5 replaced "
        "that variable with a name that Eureka resolves.")

    b.h2("3.2  The compose file")
    b.p("The compose file grew with every step, but its structure was fixed in Step 1: "
        "infrastructure first, then the Spring services, then the edge. A MySQL container is "
        "declared with four environment variables and one named volume, and it is only considered "
        "ready when <font name='Consola' size='9'>mysqladmin ping</font> answers.")
    b.code("docker-compose.yml", 14, 29)
    b.p("The health check is not decoration. MySQL accepts TCP connections several seconds before "
        "it is ready to serve queries, and a Spring Boot service that starts in that window fails "
        "at the first HikariCP connection attempt and exits. Giving MySQL a health check and "
        "making the service depend on it with <font name='Consola' size='9'>condition: "
        "service_healthy</font> turns a race into a wait.")
    b.code("docker-compose.yml", 166, 193, size=7.0)
    b.p("Two details in that block are worth pointing out. The service declares its own named "
        "volume for the database, so <font name='Consola' size='9'>docker compose down</font> does "
        "not lose the catalogue, while <font name='Consola' size='9'>down -v</font> does. And the "
        "environment block is the only place where the service learns where its dependencies are: "
        "the YAML merges an anchor into a second instance, which is how product-service is started "
        "twice in Step 5 without duplicating the configuration.")
    b.code("docker-compose.yml", 306, 311)

    b.h2("3.3  The Dockerfile")
    b.p("Every service uses the same two-stage Dockerfile. The first stage is a Maven image that "
        "compiles the sources; the second stage is a JRE image that only contains the jar. The "
        "build stage copies <font name='Consola' size='9'>pom.xml</font> first and downloads the "
        "dependencies before it copies <font name='Consola' size='9'>src</font>, so a change to a "
        "Java file reuses the cached dependency layer and only re-runs the compile.")
    b.code("product-service/Dockerfile", 1, 19)
    b.p("The multi-stage build solved a practical problem: there is no JDK on the development "
        "machine. Because Maven runs inside the image, "
        "<font name='Consola' size='9'>docker compose up --build</font> is the only command needed "
        "to go from a source tree to a running system, on any machine that has Docker. The second "
        "consequence is image size: the runtime image contains a JRE and one jar, not Maven, not "
        "the sources and not the local <font name='Consola' size='9'>~/.m2</font> repository.")

    b.h2("3.4  Configuration through environment variables")
    b.p("No service contains a host name in its compiled code. Every value that differs between "
        "environments is read as a placeholder with a default, so the same image runs in compose "
        "and would run anywhere else with a different environment. In Step 1 those placeholders "
        "were in each service's <font name='Consola' size='9'>application.yml</font>; from Step 5 "
        "the same properties are served by config-server, and the file that the product service "
        "reads now looks like this:")
    b.code("config-repo/product-service.yml", 1, 17)
    b.p("The database URL is built from <font name='Consola' size='9'>DB_URL</font>, which compose "
        "fills with <font name='Consola' size='9'>jdbc:mysql://mysql-product:3306/products</font> "
        "- a host name that only exists inside the compose network. The "
        "<font name='Consola' size='9'>useSSL=false&amp;allowPublicKeyRetrieval=true</font> part is "
        "what makes MySQL 8.4 accept a plain connection from a container without a certificate "
        "exchange, and <font name='Consola' size='9'>serverTimezone=UTC</font> keeps the timestamps "
        "of the two databases comparable.")

    b.h2("3.5  Decisions inside the services")
    b.p("The domain model is deliberately boring, because the interesting part of the project is "
        "the distribution. A product is a JPA entity with an identity-generated id, a "
        "<font name='Consola' size='9'>BigDecimal</font> price with precision 12 and scale 2, and "
        "an integer stock. Money is never a <font name='Consola' size='9'>double</font>: a total "
        "that has to be summed across order lines must not acquire a rounding error on the way.")
    b.code("product-service/src/main/java/hu/unimiskolc/shopstream/product/Product.java", 12, 33)
    b.p("The controller is a thin layer over the repository. The one decision worth recording is "
        "that the create path publishes an event and the update path evicts a cache entry - both "
        "of which were added in later steps without changing the controller's interface, which is "
        "the point of building the CRUD first.")
    b.code("product-service/src/main/java/hu/unimiskolc/shopstream/product/ProductController.java", 36, 62)
    b.p("An order is a header with a status and a total, and a list of lines that store the price "
        "that was valid when the order was placed. Copying the unit price into the order line is "
        "what makes an order a historical document: if the catalogue price changes tomorrow, the "
        "order still shows what the customer agreed to pay.")
    b.code("order-service/src/main/java/hu/unimiskolc/shopstream/order/Order.java", 19, 43)

    b.h2("3.6  Errors are part of the interface")
    b.p("A missing product has to produce a 404 with a body a client can read, not a stack trace. "
        "Each service maps its exceptions onto Spring's <font name='Consola' size='9'>ProblemDetail"
        "</font> with an <font name='Consola' size='9'>@RestControllerAdvice</font>, so the shape of "
        "an error is the same in every service and the front end can display "
        "<font name='Consola' size='9'>detail</font> without knowing which service answered. The "
        "same mechanism is what turns a validation failure into a 400 in Step 3 and a rejected "
        "order into a 409 in Step 2.")

    b.h2("3.7  What was observed")
    b.p("Fifteen containers came up with one command; only the gateway publishes a port. That is "
        "the situation at the end of Step 5 - at the end of Step 1 there was no gateway yet and the "
        "two services still published 8080 and 8081 themselves, which is why the last step is the "
        "one that changes the deployment rather than the code. The container list and a complete "
        "create-read-update-list cycle through the API are shown below.")
    b.fig("fig-containers.png", "docker compose ps after a cold start. Every container is up, and "
          "the only published port is 8080 on the gateway.")
    b.fig("fig-api-crud.png", "The product API through the gateway: POST creates, GET reads, PUT "
          "updates, GET /api/products lists the eight products that were left in the catalogue "
          "after the verification runs of this report.")


def chapter4(b):
    b.h1("4  Step 2 - The order saga over Kafka")
    b.h2("4.1  What the step asked for")
    b.p("Step 2 replaces the synchronous stock check with an event-driven one. A single Kafka "
        "broker in KRaft mode is added to compose; three topics are created from Java "
        "configuration with three partitions each; order-service stores a PENDING order and "
        "publishes <font name='Consola' size='9'>OrderPlaced</font>; product-service consumes it, "
        "reserves the stock in one database transaction, and publishes "
        "<font name='Consola' size='9'>StockReserved</font> or <font name='Consola' size='9'>"
        "StockRejected</font>; order-service consumes that and moves the order to CONFIRMED or "
        "REJECTED; notification-service writes one e-mail per finished order. The reservation has "
        "to be idempotent, because the same OrderPlaced may be delivered twice.")
    b.p("The KRaft mode means there is no ZooKeeper container: the broker is also the controller, "
        "and it elects itself. That removes one process and one failure mode from a project whose "
        "Kafka usage is a single broker anyway. <font name='Consola' size='9'>"
        "KAFKA_AUTO_CREATE_TOPICS_ENABLE</font> is set to false on purpose, so a typo in a topic "
        "name fails loudly instead of silently creating a second topic with one partition.")

    b.h2("4.2  Topics, partitions and keys")
    b.table(
        ["Topic", "Key", "Partitions", "Producers", "Consumers (group)"],
        [
            ["order-events", "orderId", "3", "order-service", "product-service, notification-service"],
            ["inventory-events", "orderId", "3", "product-service", "order-service, notification-service"],
            ["product-events", "productId", "3", "product-service", "search-service"],
        ],
        [3.4, 2.2, 2.0, 3.4, 5.6], "The three topics. The key is what keeps the events of one "
        "aggregate in order.")
    b.p("The key is the load-bearing decision. Kafka guarantees order inside a partition, not "
        "across a topic. Keying by <font name='Consola' size='9'>orderId</font> means every event "
        "about one order - placed, reserved, confirmed - lands in the same partition and is "
        "therefore seen in the order it was produced. If the key were null the events would be "
        "spread round-robin, a StockReserved could overtake its OrderPlaced, and the idempotency "
        "table would be asked to accept a result for an order it has not seen yet. Keying "
        "product-events by <font name='Consola' size='9'>productId</font> has the same purpose: "
        "two updates of the same product must not be applied to the index in the wrong order.")
    b.p("The topics are declared as beans rather than with a shell command, so a fresh "
        "environment creates them at startup and the partition count is part of the source code:")
    b.code("product-service/src/main/java/hu/unimiskolc/shopstream/product/config/KafkaTopicConfig.java", 19, 54)
    b.p("The names themselves are not in the Java code any more - they come from "
        "<font name='Consola' size='9'>shopstream.topics.*</font> in the shared configuration, "
        "which is what makes renaming a topic a one-line change instead of a recompile of four "
        "services.")

    b.h2("4.3  Producing: publish after the transaction committed")
    b.p("The obvious way to publish OrderPlaced is to call "
        "<font name='Consola' size='9'>kafkaTemplate.send</font> at the end of "
        "<font name='Consola' size='9'>OrderService.create</font>. The problem is that "
        "<font name='Consola' size='9'>create</font> is transactional: if the commit fails after "
        "the message is sent, product-service receives an order that does not exist, and the "
        "system reserves stock for a phantom. Publishing in the same transaction is not possible "
        "without a transactional outbox.")
    b.p("The solution used here is Spring's transaction-bound application events. The service "
        "publishes a plain object on the application event bus, and a listener annotated with "
        "<font name='Consola' size='9'>@TransactionalEventListener(phase = AFTER_COMMIT)</font> "
        "turns it into a Kafka message only if the transaction actually committed.")
    b.code("order-service/src/main/java/hu/unimiskolc/shopstream/order/OrderEventsPublisher.java", 22, 63)
    b.p("This is not a complete outbox - a crash between the commit and the send loses the event, "
        "because the message is not part of the database transaction. A real outbox would write "
        "the event to a table in the same transaction and let a poller publish it. For this "
        "project the AFTER_COMMIT listener removes the failure mode that matters in practice - a "
        "rolled-back write announcing itself - and Chapter 9 discusses the remaining gap honestly.")
    b.p("The two ends of the JSON contract are the serializer configuration and the event records. "
        "Every service configures <font name='Consola' size='9'>JsonSerializer</font> and "
        "<font name='Consola' size='9'>JsonDeserializer</font>, and every consumer trusts exactly "
        "one package:")
    b.code("config-repo/order-service.yml", 10, 21)
    b.p("<font name='Consola' size='9'>spring.json.trusted.packages</font> is not optional. "
        "The deserializer refuses to instantiate classes from packages it was not told about, "
        "and the default is to trust only <font name='Consola' size='9'>java.util, java.lang</font>; "
        "without this line every consumer fails on the first message with a security exception.")

    b.h2("4.4  Consuming: reserve the stock in one transaction")
    b.p("product-service listens on order-events in the consumer group "
        "<font name='Consola' size='9'>product-service</font>, ignores anything that is not an "
        "OrderPlaced, and hands the decision to a service method:")
    b.code("product-service/src/main/java/hu/unimiskolc/shopstream/product/inventory/OrderEventListener.java", 52, 90)
    b.p("The reservation itself is the part that has to be idempotent. Kafka delivers at least "
        "once: a consumer that crashes after committing the offset but before finishing its work "
        "will see the message again, and a rebalance can redeliver a batch. If the second delivery "
        "subtracted the stock a second time, an order of two keyboards would remove four.")
    b.code("product-service/src/main/java/hu/unimiskolc/shopstream/product/inventory/InventoryService.java", 34, 76)
    b.p("The guard is a row in <font name='Consola' size='9'>processed_orders</font> keyed by the "
        "order id, and it is written inside the same transaction that changes the stock. So either "
        "both happened or neither did: if the transaction rolls back, the order is not marked as "
        "processed and the next delivery can try again. If the row exists, the method returns the "
        "stored result without touching the product table, which also means a redelivered message "
        "does not publish a second, contradictory InventoryEvent.")
    b.p("Ordering the writes matters here. The stock is only decremented after every line has been "
        "checked, so a rejected order leaves the catalogue untouched; there is no partial "
        "reservation to compensate. A multi-line order that asks for three products is judged as a "
        "whole, and the reason string names the line that failed.")

    b.h2("4.5  Closing the loop")
    b.p("order-service consumes inventory-events in its own group and applies the decision, but "
        "only if the order is still PENDING - the same idempotency idea, one level up:")
    b.code("order-service/src/main/java/hu/unimiskolc/shopstream/order/OrderService.java", 75, 97)
    b.p("The status check makes the transition one-way. A duplicated StockReserved cannot confirm "
        "an order twice, and an event that arrives after the order was already rejected cannot "
        "revive it. Both cases are logged at INFO with the words <i>duplicate</i> and <i>already</i>, "
        "which is what the verification in Section 4.7 looks for.")
    b.p("notification-service is the third consumer of the same two topics, in the group "
        "<font name='Consola' size='9'>notification-service</font>. It has no database: it keeps "
        "the OrderPlaced payload in a map, waits for the final event, and formats the message. "
        "Writing an e-mail is a side effect that must not happen twice, so it keeps a set of order "
        "ids it has already notified.")
    b.code("notification-service/src/main/java/hu/unimiskolc/shopstream/notification/NotificationListener.java", 47, 65)
    b.p("The output is a log line that is shaped like an e-mail, because the assignment asks for a "
        "log entry rather than an SMTP server:")
    b.table(
        ["Consumer group", "Subscribes to", "What it does"],
        [
            ["product-service", "order-events", "Reserves or rejects stock, publishes inventory-events"],
            ["order-service", "inventory-events", "Moves the order from PENDING to CONFIRMED or REJECTED"],
            ["notification-service", "order-events, inventory-events", "Writes one simulated e-mail per finished order"],
            ["search-service", "product-events", "Maintains the Elasticsearch index (Step 3)"],
        ],
        [3.6, 4.4, 8.6], "Consumer groups. Two services can read the same topic without stealing "
        "each other's messages only because their group ids differ.")

    b.h2("4.6  Why the PENDING state is not hidden")
    b.p("A client that posts an order gets <font name='Consola' size='9'>201 Created</font> with "
        "<font name='Consola' size='9'>status: PENDING</font> immediately, and has to ask again to "
        "learn the outcome. It would be possible to hide the wait by blocking inside "
        "<font name='Consola' size='9'>POST /orders</font> until the event comes back - Step 4 does "
        "exactly that in cart-service, with a five second timeout - but at the order API itself the "
        "honest answer is the intermediate state. The order exists, it has an id, and its fate is "
        "not decided yet. Reporting that is better than a request that hangs and then times out "
        "while the order is in fact accepted.")

    b.h2("4.7  What was observed")
    b.p("Three topics with three partitions each were created by the services, not by hand:")
    b.fig("fig-kafka-topics.png", "kafka-topics --describe, filtered to the three topics of the "
          "system. Each has three partitions and replication factor one.")
    b.p("Reading the topics directly shows the key on the left and the JSON payload on the right. "
        "Order 14 is visible twice: once as the OrderPlaced that order-service produced, once as "
        "the StockReserved that product-service produced a few milliseconds later.")
    b.fig("fig-kafka-events.png", "The first message of order-events and of inventory-events, both "
          "keyed 14.")
    b.p("The order lifecycle is visible in the API as well: the POST returns PENDING, and a GET a "
        "second later returns CONFIRMED with the same total.")
    b.fig("fig-order-saga.png", "Placing an order and following it through the saga.")
    b.p("And the notification service wrote exactly one e-mail per order, with the items taken "
        "from the OrderPlaced payload and the total from the order:")
    b.fig("fig-notification-log.png", "Two simulated e-mails, for orders 14 and 15, in the log of "
          "notification-service.")


def chapter5(b):
    b.h1("5  Step 3 - Elasticsearch as a read model")
    b.h2("5.1  What the step asked for")
    b.p("Step 3 adds a search service that answers full-text queries over the product name and "
        "description, with an optional category filter, an optional price range and pagination. "
        "The index must be maintained by consuming product-events, the mapping must be explicit - "
        "name and description as text, category as keyword, price as double, stock as integer - "
        "and the query must combine a full-text match with the filters.")
    b.p("The architectural point is that search-service is not a second catalogue. The catalogue "
        "is the products table in product-service, and the index is a derived copy that could be "
        "deleted and rebuilt from the events at any time. That is why the index is allowed to "
        "exist at all under the rule that no service reads another service's data.")

    b.h2("5.2  The mapping")
    b.table(
        ["Field", "Type", "Why this type"],
        [
            ["name", "text", "Analyzed so that <i>keyboard</i> matches <i>mechanical keyboard</i>; not sortable, and does not need to be"],
            ["description", "text", "Same reason; the full-text query searches name and description together"],
            ["category", "keyword", "Filtered with a term query and used by the category dropdown, so it must not be analyzed"],
            ["price", "double", "Range filters and sorting"],
            ["stock", "integer", "Displayed as a badge; also updated by the same events after a reservation"],
        ],
        [2.6, 2.2, 11.6], "The explicit mapping of the products index.")
    b.p("The mapping is declared on the document class with <font name='Consola' size='9'>"
        "@Field</font>, and the index is created from it at startup:")
    b.code("search-service/src/main/java/hu/unimiskolc/shopstream/search/ProductDocument.java", 17, 36)
    b.code("search-service/src/main/java/hu/unimiskolc/shopstream/search/IndexInitializer.java", 27, 36)
    b.p("Without the explicit mapping Elasticsearch would guess: it would map "
        "<font name='Consola' size='9'>category</font> as text with a "
        "<font name='Consola' size='9'>.keyword</font> sub-field, and a term query on "
        "<font name='Consola' size='9'>category</font> would then fail, because the analyzed field "
        "contains lowercased tokens rather than the original value. Guessing is also unstable "
        "across documents: the mapping is fixed by the first document indexed, so one product with "
        "a numeric-looking name could change the type of a field for the whole index. Declaring it "
        "once, in code, removes both problems and documents the schema in the place a reader looks "
        "first.")

    b.h2("5.3  Keeping the index up to date")
    b.p("search-service subscribes to product-events in the group "
        "<font name='Consola' size='9'>search-service</font> and translates the three event types "
        "into index operations. There is no call from product-service to search-service, and no "
        "shared database:")
    b.code("search-service/src/main/java/hu/unimiskolc/shopstream/search/ProductIndexListener.java", 28, 43)
    b.p("The consumer is configured with <font name='Consola' size='9'>auto-offset-reset: earliest"
        "</font>. That is a deliberate choice for a rebuildable read model: when the index is "
        "recreated - or when the container starts against a topic that already holds history - the "
        "consumer replays the topic from the beginning and rebuilds the index, instead of starting "
        "at the end and serving an index that is missing everything produced before it started.")
    b.code("config-repo/search-service.yml", 1, 16)
    b.p("Because the events carry the stock as well, the index also stays fresh after a "
        "reservation: when product-service decrements the stock it publishes ProductUpdated for "
        "the affected products, and the badge on the storefront changes without anybody calling "
        "the search service.")

    b.h2("5.4  The query")
    b.p("The controller exposes the six parameters the step asks for, and the validation lives in "
        "the service so that every caller gets the same answer:")
    b.code("search-service/src/main/java/hu/unimiskolc/shopstream/search/SearchController.java", 24, 33)
    b.p("The query is built with <font name='Consola' size='9'>BoolQuery.Builder</font> and "
        "executed through <font name='Consola' size='9'>ElasticsearchOperations</font>, because a "
        "derived repository method cannot express three optional clauses at once:")
    b.code("search-service/src/main/java/hu/unimiskolc/shopstream/search/ProductSearchService.java", 32, 72)
    b.p("Two decisions in those thirty lines are worth explaining. The full-text match goes into "
        "<font name='Consola' size='9'>must</font>, which contributes to the score, while the "
        "category and price conditions go into <font name='Consola' size='9'>filter</font>, which "
        "does not: a term filter that only restricts the result set should not influence the "
        "relevance ranking, and filters are cached by Elasticsearch. Second, the text clause is a "
        "<font name='Consola' size='9'>multi_match</font> over name and description rather than two "
        "separate matches, so one query word found in the description and another found in the "
        "name still produce a hit - which is what a shopper typing <i>brown switches</i> expects.")
    b.p("The <font name='Consola' size='9'>size</font> parameter is capped at 100 and "
        "<font name='Consola' size='9'>minPrice &gt; maxPrice</font> is rejected with a 400 rather "
        "than returning an empty page, because those two cases are caller mistakes, not empty "
        "results:")
    b.fig("fig-api-search.png", "The search API: a full-text hit, a category and price range "
          "combination, pagination, and the 400 returned when the range is inverted.")
    b.p("The screenshot also shows the behaviour that makes the read model credible: after "
        "PUT /api/products/15 changed the price to 39.00 and the stock to 12, the next search "
        "returned the new values without any direct call to search-service. The product event did "
        "that, and the same mechanism removed the product from the index when it was deleted.")
