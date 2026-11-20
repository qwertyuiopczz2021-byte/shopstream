
# -*- coding: utf-8 -*-
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import NextPageTemplate, PageBreak, Paragraph, Spacer, Table, TableStyle
from report_lib import ACCENT, BODY, INK, MUTED, RULE, make_toc


def cover(b):
    st = b.story
    title = ParagraphStyle("Title", fontName="Segoe-Bold", fontSize=30, leading=35,
                           textColor=INK, alignment=TA_LEFT, spaceAfter=6)
    sub = ParagraphStyle("Sub", fontName="Segoe", fontSize=13.5, leading=19,
                         textColor=MUTED, alignment=TA_LEFT)
    small = ParagraphStyle("Small", fontName="Segoe", fontSize=10, leading=15,
                           textColor=INK, alignment=TA_LEFT)
    st.append(Spacer(1, 3.2 * cm))
    st.append(Paragraph("ShopStream", title))
    st.append(Paragraph("A distributed e-commerce platform built with Spring Boot, "
                        "Docker, Kafka, Elasticsearch, Redis and Spring Cloud", sub))
    st.append(Spacer(1, 2.2 * cm))
    rows = [
        ["Course", "Development of Distributed Web Applications"],
        ["Student", "Chen Zizheng"],
        ["Neptun", "EO8UMY"],
        ["Institution", "University of Miskolc, Faculty of Informatics"],
        ["Supervisor", "Dr. Fadi Atallah"],
        ["Submission", "4 December 2026"],
        ["Repository", "https://github.com/qwertyuiopczz2021-byte/shopstream"],
    ]
    data = [[Paragraph(k, ParagraphStyle("k", fontName="Segoe-Bold", fontSize=9.4, leading=14, textColor=MUTED)),
             Paragraph(v, small)] for k, v in rows]
    t = Table(data, colWidths=[3.0 * cm, 12.6 * cm])
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    st.append(t)
    st.append(Spacer(1, 1.6 * cm))
    st.append(Paragraph("This report describes how each of the five steps of the project was "
                        "implemented: which classes, annotations and configuration were used, "
                        "why they were used, and what the running system was observed to do.",
                        sub))
    st.append(NextPageTemplate("Body"))
    st.append(PageBreak())


def front_matter(b):
    st = b.story
    st.append(Paragraph("Contents", ParagraphStyle("TOCHead", fontName="Segoe-Bold", fontSize=18,
                                                   leading=22, textColor=ACCENT, spaceAfter=18)))
    st.append(make_toc())


def chapter1(b):
    b.h1("1  Introduction")
    b.h2("1.1  The assignment")
    b.p("The semester project of the course <i>Development of Distributed Web Applications</i> "
        "is a distributed e-commerce platform called ShopStream. The specification splits the "
        "work into five steps, and each step adds one distributed-systems problem to the same "
        "system: containers in Step 1, event-driven messaging in Step 2, a search index kept in "
        "sync by events in Step 3, a shared cache and a second data store in Step 4, and service "
        "discovery, centralised configuration and an API gateway in Step 5.")
    b.p("Two rules run through all five steps and shape most of the design decisions in this "
        "report. The first is that every service owns its data: a service may only read and write "
        "its own database, and no service may query another service's tables. The second is that "
        "the only ways for two services to talk are a REST call or a Kafka message. Those two "
        "rules are the reason the system looks the way it does, and most of the reasoning in the "
        "following chapters is an application of them.")
    b.p("The deliverable is a GitHub repository that contains the whole system, a "
        "<font name='Consola' size='9'>docker-compose.yml</font> that starts it, a README that "
        "explains how to run it, and this report. The system is demonstrated live on 9 December.")

    b.h2("1.2  What was built")
    b.p("ShopStream is eight Spring Boot applications and one static web front end, plus five "
        "infrastructure containers. The eight applications are five business services "
        "(product, order, cart, search, notification) and three Spring Cloud services "
        "(discovery, config, gateway). The infrastructure is two MySQL instances, a Kafka broker, "
        "an Elasticsearch node and a Redis instance.")
    b.table(
        ["Container", "Kind", "Responsibility"],
        [
            ["api-gateway", "Spring Cloud Gateway", "The only published port (8080). Routes /api/** to services by name, adds X-Request-Id."],
            ["frontend", "nginx + static JS", "The storefront. Served through the gateway under /."],
            ["product-service (x2)", "Spring Boot", "Product CRUD, stock reservation, product cache. Owns the products table."],
            ["order-service", "Spring Boot", "Creates orders, calls product-service for prices, follows the saga. Owns the orders table."],
            ["cart-service", "Spring Boot", "Cart CRUD and checkout. Stores carts in Redis, no relational database."],
            ["search-service", "Spring Boot", "Full-text and filtered search. Owns the Elasticsearch products index."],
            ["notification-service", "Spring Boot", "Writes one simulated e-mail per finished order. Owns nothing."],
            ["discovery-server", "Eureka", "Service registry on 8761."],
            ["config-server", "Spring Cloud Config", "Serves config-repo/*.yml on 8888."],
            ["mysql-product / mysql-order", "MySQL 8.4", "One database per service, on its own named volume."],
            ["kafka", "cp-kafka 7.6.1", "Single broker in KRaft mode, three topics with three partitions each."],
            ["elasticsearch", "Elasticsearch 8.13.4", "Single node, security disabled, 512 MB heap."],
            ["redis", "Redis 7.2", "Cart hashes and the product cache, protected by a password."],
        ],
        [3.5, 3.2, 9.9], "The fifteen containers of the running system.")
    b.p("The technical baseline is Spring Boot 3.3.13 on Java 21, Spring Cloud 2023.0.6, and the "
        "image versions listed above. Nothing in the system is mocked: the report describes "
        "observations made on the running compose stack.")

    b.h2("1.3  How this report is organised")
    b.p("Chapter 2 describes the architecture as a whole. Chapters 3 to 7 follow the five steps "
        "in order; each chapter states what the step asked for, shows the classes, annotations and "
        "configuration that implement it, explains why they were chosen, and ends with the output "
        "that was observed when the step was verified. Chapter 8 collects the verification work "
        "and the failure experiments that do not belong to a single step. Chapter 9 discusses what "
        "was difficult, what is still weak and what I would do differently, and Chapter 10 "
        "concludes. The appendices contain the HTTP API, the configuration reference and the "
        "commands needed to run the system.")

    b.h2("1.4  Environment and tooling")
    b.p("The whole system is developed and run on Windows 11 with Docker Desktop. Two constraints "
        "shaped the tooling. First, there is no JDK installed on the host: Maven only ever runs "
        "inside the build stage of a Docker image, so the host needs nothing but Docker. Second, "
        "the host is not the deployment target, so every check in this report was made against "
        "containers, through the gateway, and not against an IDE run configuration.")
    b.bullets([
        "Docker Desktop 29.8.0 with the Linux engine; the compose project is named "
        "<font name='Consola' size='9'>shopstream</font>, so every container is called "
        "<font name='Consola' size='9'>shopstream-*</font>.",
        "Git 2.53 with the repository pushed to GitHub after every step, so the commit history "
        "shows how the system grew instead of one final upload.",
        "The verification commands in this report are PowerShell, because that is the shell on "
        "the development machine; <font name='Consola' size='9'>Invoke-RestMethod</font> is used "
        "instead of curl, and the screenshots show its real output.",
        "The front end is plain HTML, CSS and JavaScript served by nginx: no build step, no "
        "framework, because the assignment is about the distributed back end.",
    ])


def chapter2(b):
    b.h1("2  Architecture")

    b.h2("2.1  Services and their boundaries")
    b.p("The system is cut along business capabilities, not along technical layers. Product "
        "catalogue, ordering, cart, search and notification each became a service because each "
        "one has its own data, its own rate of change and its own reason to exist. The three "
        "Spring Cloud services are infrastructure: they do not hold business data, and the "
        "business services would work without them if the URLs were hard-coded - which is exactly "
        "what Step 1 to Step 4 did, and what Step 5 removed.")
    b.p("Each business service has one owner for each piece of data:")
    b.table(
        ["Data", "Owner", "Store", "Who may read it"],
        [
            ["Product catalogue and stock", "product-service", "MySQL <i>products</i>, <i>processed_orders</i>", "product-service only; everybody else through its API or its events"],
            ["Orders and order lines", "order-service", "MySQL <i>orders</i>, <i>order_items</i>", "order-service only"],
            ["Cart contents", "cart-service", "Redis hash <i>carts:{userId}</i>", "cart-service only"],
            ["Searchable product view", "search-service", "Elasticsearch index <i>products</i>", "search-service only (a read model)"],
            ["E-mail log", "notification-service", "nothing - the log is the output", "-"],
        ],
        [3.9, 3.1, 4.6, 5.0], "Data ownership. No service reads another service's store.")
    b.p("The cart is the one place where the assignment allows a service without a relational "
        "database, and the search index is deliberately a read model: it is built from "
        "product-service's events and holds no data that product-service does not own. That is "
        "what makes it acceptable for search-service to store a copy of the catalogue - the copy "
        "is derived, and it can be thrown away and rebuilt.")

    b.h2("2.2  Two ways to talk")
    b.p("Every interaction in ShopStream is either a synchronous REST call on the request path or "
        "an asynchronous Kafka message after the fact. The split follows one question: does the "
        "caller need the answer in order to continue?")
    b.bullets([
        "<b>Synchronous, request path.</b> The storefront asks the gateway, the gateway asks a "
        "service, and order-service asks product-service for a price while it is creating an "
        "order. The caller cannot continue without the answer, so a REST call through Feign is the "
        "right shape, and a failure has to be turned into an HTTP error the same second.",
        "<b>Asynchronous, after the fact.</b> Reserving stock, re-indexing a product and writing "
        "the confirmation e-mail do not have to happen while the customer waits. They are events "
        "on Kafka, and the system tolerates them arriving a second later.",
        "<b>Why not one or the other.</b> Doing the stock reservation synchronously inside the "
        "order request would make order-service and product-service fail together, and the "
        "assignment explicitly asks for the PENDING-then-CONFIRMED lifecycle. Doing the price "
        "lookup asynchronously would mean the customer is told a total before the total is known.",
    ])
    b.fig("fig-request-path.png", "The synchronous path. Only the gateway publishes a port; the "
          "front end is served through it, and every API route is an lb:// URI resolved in Eureka.")
    b.p("Figure 1 shows the path a request takes once Step 5 is in place. The browser talks to one "
        "host and one port. The gateway looks at the path, picks the route, asks Eureka where that "
        "service currently is, and forwards the request with the <font name='Consola' size='9'>/api"
        "</font> prefix stripped. The service behind it has no idea that a gateway exists: it "
        "still serves <font name='Consola' size='9'>/products/{id}</font>, exactly as in Step 1.")

    b.h2("2.3  The order saga")
    b.p("Placing an order is the one business process that spans two services and two databases, "
        "so it is worth describing on its own. ShopStream implements it as a choreographed saga: "
        "there is no orchestrator process, each service reacts to the event it receives and "
        "publishes the event that follows from it.")
    b.fig("fig-saga-flow.png", "The order saga. The order is stored as PENDING first; the stock "
          "decision arrives as an event and moves it to CONFIRMED or REJECTED.")
    b.p("The sequence is: order-service validates the request, asks product-service for the price "
        "of every line, stores the order as PENDING, and publishes <font name='Consola' size='9'>"
        "OrderPlaced</font> in the same transaction. product-service consumes it, decides whether "
        "the stock is available, and publishes <font name='Consola' size='9'>InventoryEvent</font> "
        "with status STOCK_RESERVED or STOCK_REJECTED. order-service consumes that event and moves "
        "the order to CONFIRMED or REJECTED; notification-service consumes the same event in its "
        "own consumer group and writes the e-mail.")
    b.p("The interesting property of this design is what it does <i>not</i> need: no distributed "
        "transaction, no two-phase commit, no shared table. Each service commits to its own "
        "database, and the intermediate state - an order that is PENDING - is visible and "
        "meaningful instead of being a lock. The price of that is eventual consistency: for a "
        "moment the customer can see an order whose fate is not decided yet, which is why the API "
        "returns PENDING instead of pretending the order is already confirmed.")

    b.h2("2.4  Keeping the read model honest")
    b.p("The search index and the product cache are two copies of data that product-service owns, "
        "and both are refreshed by events rather than by the writers calling them directly. "
        "product-service publishes <font name='Consola' size='9'>ProductCreated</font>, "
        "<font name='Consola' size='9'>ProductUpdated</font> and <font name='Consola' size='9'>"
        "ProductDeleted</font> from a transaction listener, so the event is only sent after the "
        "database transaction committed.")
    b.fig("fig-product-events.png", "The catalogue pushes its changes into the search index; the "
          "same events carry the new stock figure after a reservation.")
    b.p("This is the same idea as the saga, applied to a cache: the authoritative write happens "
        "once, in product-service, and every derived copy follows it. Chapter 5 shows how "
        "search-service turns those events into index writes, and Chapter 6 shows how the same "
        "events evict the cache entry that StockReserved made stale.")

    b.h2("2.5  The storefront")
    b.p("The front end exists to make the system demonstrable: it is a single page with a "
        "catalogue, a cart and an order tracker, written in plain JavaScript and served by nginx. "
        "It calls only <font name='Consola' size='9'>/api/...</font> URLs, so in Step 5 nothing in "
        "it had to change when the gateway took over routing - the same code that used to talk to "
        "four ports talks to one. The page is bilingual (English and Chinese) because the "
        "screenshots in this report were taken on both, and the language switch is a second "
        "dictionary in the same file.")
    b.fig(r"D:\projects\shopstream\docs\screenshots\store.png",
          "The storefront: catalogue from search-service, stock badges, category and price filters.")
