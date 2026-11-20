
# -*- coding: utf-8 -*-
from reportlab.lib.units import cm


def chapter6(b):
    b.h1("6  Step 4 - Redis for carts and for the catalogue cache")
    b.h2("6.1  What the step asked for")
    b.p("Step 4 introduces two different uses of the same store. The first is a shopping cart: "
        "cart-service must keep a cart per user in Redis with <font name='Consola' size='9'>"
        "@RedisHash(\"carts\")</font> and a <font name='Consola' size='9'>CrudRepository</font>, "
        "offer read / add / change quantity / remove / clear, and expire an untouched cart after a "
        "period that has to be written down in the README. Checking out must send the cart to "
        "order-service and clear it <i>only if the order is accepted</i>. The second use is a "
        "read cache in product-service: <font name='Consola' size='9'>GET /products/{id}</font> is "
        "cached, and the entry is evicted when the product changes or when stock is reserved.")
    b.p("The two uses are worth separating because they have opposite lifetimes. A cart is the "
        "only copy of the data and has to survive a restart of the service; a cached product is a "
        "copy of something that already exists in MySQL and may disappear at any moment without "
        "anyone noticing. Redis is a good home for both, but for different reasons: durability for "
        "the first, cheap shared state for the second.")

    b.h2("6.2  The cart is one Redis hash")
    b.p("A cart is stored as a single hash at the key <font name='Consola' size='9'>carts:{userId}"
        "</font>, where the field is the product id and the value is the quantity. The class is a "
        "plain object with Spring Data Redis annotations; there is no table and no schema.")
    b.code("cart-service/src/main/java/hu/unimiskolc/shopstream/cart/Cart.java", 20, 32)
    b.p("Three decisions are encoded in those few lines. The key is the user id, so a cart is "
        "addressed by its owner and the repository needs no query method at all - "
        "<font name='Consola' size='9'>findById(userId)</font> is the whole API. The TTL is a "
        "field rather than a Redis <font name='Consola' size='9'>EXPIRE</font> command, so every "
        "save rewrites it and the clock restarts: a cart that is used stays, a cart that is "
        "abandoned disappears after seven days. And the quantity map is a "
        "<font name='Consola' size='9'>Map&lt;Long, Integer&gt;</font> inside the hash, which means "
        "adding an item is a read-modify-write of one document instead of an insert into a second "
        "table.")
    b.p("The seven-day figure is the answer to the requirement that the expiry period be "
        "documented, and it is in the README next to the API. It is a compromise: long enough that "
        "a customer can come back the next day and find the basket, short enough that abandoned "
        "carts do not accumulate forever in a store that never deletes anything.")
    b.p("The controller is thin, and the interesting behaviour is in the service:")
    b.code("cart-service/src/main/java/hu/unimiskolc/shopstream/cart/CartController.java", 19, 60)
    b.p("Removing the last item deletes the key instead of storing an empty hash, so "
        "<font name='Consola' size='9'>KEYS carts:*</font> never returns a cart that has nothing in "
        "it. That is a small thing, but it keeps the Redis contents equal to the set of carts that "
        "exist, which is what makes the inspection in Section 6.5 readable.")

    b.h2("6.3  Checkout has to wait for a decision")
    b.p("The requirement that the cart is cleared only if the order is accepted collides with the "
        "asynchronous design of Step 2: <font name='Consola' size='9'>POST /orders</font> answers "
        "PENDING, and the accept or reject arrives later on inventory-events. cart-service "
        "therefore places the order, waits a bounded time for a terminal status, and only then "
        "decides what to do with the cart.")
    b.code("cart-service/src/main/java/hu/unimiskolc/shopstream/cart/CartService.java", 77, 118)
    b.p("The wait is a poll with a deadline rather than a blocking call, and both numbers are "
        "configuration: five seconds of timeout and a 250 millisecond interval. Polling is the "
        "honest choice here because the alternative - subscribing to inventory-events inside "
        "cart-service - would duplicate order-service's job and would still leave the HTTP request "
        "waiting. A poll of one order id is cheap; a second consumer group that has to correlate "
        "events with open HTTP requests is not.")
    b.p("The three outcomes are all handled, and the third is the one that matters: if the order is "
        "still PENDING when the deadline passes, the cart is kept. The response says so - "
        "<i>Order still PENDING after 5000 ms, cart kept</i> - and the customer can try again. "
        "Clearing the cart on a timeout would lose the basket of an order that may in fact have "
        "been confirmed a millisecond later.")

    b.h2("6.4  A cache that cannot serve a stale price")
    b.p("Caching a product is easy; invalidating it correctly is the actual task. The cache is "
        "configured with an explicit time to live as a safety net, and with a rule that nulls are "
        "not cached, because a cached 404 would survive the creation of the product it says does "
        "not exist:")
    b.code("product-service/src/main/java/hu/unimiskolc/shopstream/product/CacheConfig.java", 18, 29)
    b.p("The read path uses cache-aside, and the write paths evict:")
    b.code("product-service/src/main/java/hu/unimiskolc/shopstream/product/ProductController.java", 41, 52)
    b.p("<font name='Consola' size='9'>PUT</font> and <font name='Consola' size='9'>DELETE</font> "
        "carry <font name='Consola' size='9'>@CacheEvict(cacheNames = \"products\", key = \"#id\")"
        "</font> on the same two lines, so a price change is visible on the next read. The third "
        "write path is the inventory listener: when a reservation succeeds, the stock of every "
        "affected product changes without any HTTP request touching that product, so the eviction "
        "is called explicitly from a small bean:")
    b.code("product-service/src/main/java/hu/unimiskolc/shopstream/product/ProductCache.java", 11, 18)
    b.p("Without that call the storefront would keep offering <i>15 in stock</i> for a product that "
        "has been sold out, until the ten minute TTL expired. This is the general shape of a cache "
        "in an event-driven system: every writer has to know that it is a writer, including the "
        "ones that are not HTTP endpoints.")
    b.code("config-repo/cart-service.yml", 1, 14)

    b.h2("6.5  What was observed")
    b.p("Inspecting Redis directly shows the hash, its class and its TTL. The "
        "<font name='Consola' size='9'>_class</font> field is written by Spring Data so that a "
        "generic Redis client can still tell what the hash represents, and "
        "<font name='Consola' size='9'>ttl 604800</font> is the seven days in seconds.")
    b.fig("fig-redis-cart.png", "The cart of user guest in Redis: the hash, its fields, its class "
          "and the seven day TTL.")
    b.p("The checkout endpoint answers with the order id, the final status and whether the cart was "
        "cleared - the three facts a client needs to decide what to show next:")
    b.fig("fig-checkout.png", "POST /api/carts/guest/checkout: the order was confirmed, so "
          "cartCleared is true.")
    b.p("The same flow through the storefront shows the cart before checkout, with quantities and "
        "the total computed by cart-service rather than by the browser:")
    b.fig("../../screenshots/cart.png", "The cart page. Every number on it comes from cart-service; "
          "the page only formats them.", width_cm=15.0)


def chapter7(b):
    b.h1("7  Step 5 - Service discovery, configuration and a single entry point")
    b.h2("7.1  What the step asked for")
    b.p("The last step turns six independently running services into a system. A Eureka server has "
        "to register every service, with product-service running two instances. A config server "
        "has to serve the database URLs, the Kafka settings and the topic names, plus a shared "
        "configuration file. The hard-coded HTTP calls have to be replaced by Feign interfaces "
        "that use service names only. An api-gateway has to route <font name='Consola' size='9'>"
        "/api/products/**</font> and its three siblings to <font name='Consola' size='9'>lb://"
        "</font> targets with <font name='Consola' size='9'>StripPrefix</font>, and a custom global "
        "filter has to set and log an <font name='Consola' size='9'>X-Request-Id</font> header. "
        "Finally, only the gateway may publish a port.")
    b.p("The three parts solve three different problems, and it is worth keeping them apart. "
        "Discovery answers <i>where is product-service right now</i>; configuration answers <i>what "
        "are the settings</i>; the gateway answers <i>how does a client reach any of this at all</i>. "
        "The first two are infrastructure for the services, the third is the only public surface.")

    b.h2("7.2  The registry")
    b.p("discovery-server is a twenty-six line application whose only significant annotation is "
        "<font name='Consola' size='9'>@EnableEurekaServer</font>. The interesting part is its "
        "configuration, because a registry has to be told not to do the two things every other "
        "service does:")
    b.code("discovery-server/src/main/resources/application.yml", 1, 16)
    b.p("<font name='Consola' size='9'>register-with-eureka</font> and "
        "<font name='Consola' size='9'>fetch-registry</font> are both false because this process "
        "<i>is</i> the registry: registering itself and fetching its own registry is a loop that "
        "produces one confusing log line every thirty seconds and nothing else. "
        "<font name='Consola' size='9'>enable-self-preservation</font> is off because self-preservation "
        "is designed for a production cluster, where losing every heartbeat at once means the "
        "network is broken rather than that the services are down. In a compose file where a "
        "service can be stopped with one command, the protective behaviour is exactly wrong: it "
        "keeps listing an instance that has been shut down for minutes. Turning it off makes the "
        "registry drop a stopped instance after roughly ninety seconds - the lease is thirty "
        "seconds and Eureka expires after three renewals - which is slow enough to be safe and "
        "fast enough to demonstrate.")
    b.p("Every other service registers with the shared configuration, which lives in one place:")
    b.code("config-repo/application.yml", 8, 37)
    b.p("<font name='Consola' size='9'>prefer-ip-address: true</font> is a container-specific "
        "decision. By default Eureka registers the host name of the container, which is a random "
        "hex id that only Docker's DNS can resolve. The gateway and Feign clients would then depend "
        "on that name resolving from inside whichever container asks. Registering the IP address is "
        "what makes <font name='Consola' size='9'>lb://product-service</font> work between two "
        "containers that were started in a different order.")

    b.h2("7.3  Configuration outside the jars")
    b.p("config-server runs in the <font name='Consola' size='9'>native</font> profile, which means "
        "it serves files from a directory instead of cloning a Git repository:")
    b.code("config-server/src/main/resources/application.yml", 1, 16)
    b.p("The directory is <font name='Consola' size='9'>./config-repo</font> in the repository, "
        "mounted into the container at <font name='Consola' size='9'>/config-repo</font>. That "
        "choice is a compromise the assignment allows: the step asks for a Git repository <i>or</i> "
        "a folder inside the repository. A folder keeps the configuration versioned with the code "
        "it configures - the same commit that changes a route also changes the route's "
        "configuration - and it works offline, which a Git URL would not on the day of the "
        "presentation. A real deployment would point "
        "<font name='Consola' size='9'>search-locations</font> at a Git URL and get the same "
        "semantics.")
    b.p("The layout follows Spring Cloud Config's convention: <font name='Consola' size='9'>"
        "application.yml</font> is read by every service, and "
        "<font name='Consola' size='9'>{service-name}.yml</font> is read by that service on top of "
        "it. Six service files plus the shared one hold everything that used to be in eight "
        "<font name='Consola' size='9'>application.yml</font> files inside the jars.")
    b.table(
        ["File in config-repo", "What it holds"],
        [
            ["application.yml", "Eureka URL, IP registration, Feign timeouts, topic names and partition counts"],
            ["product-service.yml", "Datasource, JPA, Kafka producer, cache TTL"],
            ["order-service.yml", "Datasource, Kafka producer and consumer"],
            ["cart-service.yml", "Redis host and password, checkout timeout and poll interval"],
            ["search-service.yml", "Elasticsearch URI, Kafka consumer with earliest offset"],
            ["notification-service.yml", "Kafka consumer, notification settings"],
            ["api-gateway.yml", "The five routes"],
        ],
        [4.6, 11.8], "The configuration repository. Everything that differs between a laptop and "
        "a cluster lives here, not in the images.")
    b.p("Each service keeps a two-line bootstrap in its own "
        "<font name='Consola' size='9'>application.yml</font>: its name and "
        "<font name='Consola' size='9'>spring.config.import: \"optional:configserver:http://config-server:8888\""
        "</font>. The <font name='Consola' size='9'>optional:</font> prefix is deliberate. Without "
        "it a service that starts while config-server is still booting fails immediately and the "
        "whole compose start becomes order-dependent. With it the service starts on its defaults "
        "and picks up the configuration when the config server answers.")

    b.h2("7.4  Feign instead of a URL")
    b.p("In Step 1 order-service called product-service through a "
        "<font name='Consola' size='9'>RestClient</font> built from an environment variable. Feign "
        "replaces the URL with a service name and the hand-written error handling with a decoder:")
    b.code("order-service/src/main/java/hu/unimiskolc/shopstream/order/ProductFeignClient.java", 16, 21)
    b.p("That interface is the whole client. <font name='Consola' size='9'>name = \"product-service\""
        "</font> is what the load balancer resolves through Eureka, so the call goes to whichever "
        "of the two instances is available, and <font name='Consola' size='9'>path</font> keeps the "
        "controller's own mapping out of every method signature. The interface is discovered by "
        "<font name='Consola' size='9'>@EnableFeignClients</font> on the application class.")
    b.p("What Feign does not do by itself is translate HTTP status codes into the domain exceptions "
        "the service already throws. That is one class:")
    b.code("order-service/src/main/java/hu/unimiskolc/shopstream/order/FeignErrorConfig.java", 19, 36)
    b.p("The default decoder would turn every 4xx and 5xx into "
        "<font name='Consola' size='9'>FeignException</font>, and the API would answer 500 for a "
        "product that does not exist. Translating 404 into "
        "<font name='Consola' size='9'>ProductNotFoundException</font> restores the correct 404, "
        "and translating the 5xx family into <font name='Consola' size='9'>ProductUnavailableException"
        "</font> produces a 503 with a message that says <i>the catalogue is unreachable</i> rather "
        "than a stack trace. Unknown statuses are handed back to the default decoder, so the "
        "translation is a filter, not a replacement.")
    b.p("cart-service has the same shape, one hop further along the saga:")
    b.code("cart-service/src/main/java/hu/unimiskolc/shopstream/cart/OrderClient.java", 18, 33)
    b.p("A default method on the interface is a small but useful trick: it keeps the two calls - "
        "place the order, then poll it - next to the endpoint that serves them, so the checkout "
        "logic in the service reads as business logic rather than as HTTP plumbing.")

    b.h2("7.5  The gateway")
    b.p("The gateway is configured entirely in the config repository, which is the point of having "
        "a config server. Route order matters in Spring Cloud Gateway, and the routes are written "
        "so that the specific prefixes are tested before the catch-all:")
    b.code("config-repo/api-gateway.yml", 1, 36)
    b.p("Each of the four API routes has three parts with three separate jobs. "
        "<font name='Consola' size='9'>Path=/api/products,/api/products/**</font> decides which "
        "requests the route owns - both the bare prefix and anything under it, because "
        "<font name='Consola' size='9'>/api/products/**</font> does not match "
        "<font name='Consola' size='9'>/api/products</font> in Spring's pattern syntax. "
        "<font name='Consola' size='9'>StripPrefix=1</font> removes the "
        "<font name='Consola' size='9'>/api</font> segment, so product-service still sees "
        "<font name='Consola' size='9'>GET /products/8</font> and its controllers do not have to "
        "know that a gateway exists. <font name='Consola' size='9'>lb://product-service</font> hands "
        "the call to the load balancer, which asks Eureka for the instances and picks one; that is "
        "why stopping one of the two product-service containers does not break the storefront.")
    b.p("The fifth route is the front end, and it has no load balancer because nginx is a single "
        "container with a fixed name. It is last and its pattern is "
        "<font name='Consola' size='9'>/**</font>, so it catches everything that is not an API "
        "path - which includes the page itself, app.js and the stylesheet.")
    b.p("The custom filter is where the requirement about the request id is implemented:")
    b.code("api-gateway/src/main/java/hu/unimiskolc/shopstream/gateway/RequestIdFilter.java", 25, 54)
    b.p("Two details make it useful rather than decorative. The filter reuses an incoming "
        "<font name='Consola' size='9'>X-Request-Id</font> if the caller supplied one, and only "
        "generates a UUID when it did not - so a client can correlate its own logs with the "
        "server's. And the header is written back onto the <i>response</i> as well, which means a "
        "user reporting a broken page can quote an id that appears in every service log that "
        "touched the request. <font name='Consola' size='9'>HIGHEST_PRECEDENCE</font> ensures the id "
        "exists before any routing filter runs, so the log line that follows contains it.")

    b.h2("7.6  One published port, and what happens when an instance dies")
    b.p("The compose file publishes exactly one host port. Everything else is reachable only on "
        "the compose network, which is what a gateway is for: the services behind it are not an "
        "API surface, they are implementation.")
    b.fig("fig-gateway-routes.png", "The routes as the gateway sees them, from its actuator "
          "endpoint.")
    b.p("The registry lists all seven applications, with two instances of product-service - the "
        "evidence that the second replica is registered rather than merely running:")
    b.fig("../../screenshots/eureka.png", "The Eureka dashboard. PRODUCT-SERVICE shows UP (2), the "
          "others UP (1).", width_cm=15.0)
    b.p("Stopping one product-service container while the storefront is being used is the test that "
        "separates a working load balancer from a working-looking one. The first requests after the "
        "stop can still fail, because Eureka has not yet expired the lease and the gateway is still "
        "routing to an address that no longer answers; after about a minute the registry has "
        "dropped the instance and every request goes to the survivor.")
    b.fig("fig-failover.png", "Requests to /api/products/8 while one product-service instance is "
          "stopped and then started again.")
    b.p("The mixed first line - 500, 200, 500, 200 - is the interesting part of the evidence. It is "
        "not a bug in the gateway: the load balancer was round-robining between a live and a dead "
        "instance, and the dead one only left the registry when its lease expired. The fix for a "
        "production system is a retry filter on the route plus a shorter lease; for this project "
        "the behaviour is documented, because a report that showed only 200s would be hiding the "
        "most instructive minute of the whole step.")
    b.fig("../../screenshots/gateway-store.png", "The storefront served through the gateway on port "
          "8080, with the language switch added in the last commit.", width_cm=15.0)

    b.h2("7.7  The failure that cost the most time")
    b.p("The gateway did not start on the first attempt. It failed during context refresh with "
        "<font name='Consola' size='9'>java.lang.NoSuchMethodError: 'java.util.Set "
        "org.springframework.http.HttpHeaders.headerSet()'</font>, thrown from "
        "<font name='Consola' size='9'>RemoveHopByHopHeadersFilter.filter</font> - code inside the "
        "gateway itself, not in this project.")
    b.p("The cause is a version skew between two artifacts that are normally managed together. "
        "<font name='Consola' size='9'>spring-cloud-starter-gateway</font> pulls in "
        "<font name='Consola' size='9'>spring-cloud-gateway-server 4.1.9</font>, which calls "
        "<font name='Consola' size='9'>headerSet()</font> - a method added in Spring Framework "
        "6.1.21 - while Spring Boot 3.3.4 pins Framework 6.1.13. The method does not exist in the "
        "pinned version, and the filter fails at first use. Upgrading every service to Boot 3.3.13, "
        "which manages Framework 6.1.21, fixed it without touching any application code. The lesson "
        "is in Chapter 9: in a multi-module Maven build, the BOM is a shared decision, and a single "
        "module on an older patch level can break a feature that that module does not even use.")
