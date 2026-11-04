package hu.unimiskolc.shopstream.notification;

import hu.unimiskolc.shopstream.events.InventoryEvent;
import hu.unimiskolc.shopstream.events.OrderPlaced;
import hu.unimiskolc.shopstream.events.Topics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Stands in for the mail server: it listens to both topics and writes one
 * "email" to the log for every order that reached a final state.
 *
 * order-events tells us what was ordered, inventory-events tells us whether the
 * stock was reserved. Both listeners share the group notification-service, so a
 * second notification instance would split the partitions with this one instead of
 * sending every mail twice.
 */
@Component
public class NotificationListener {

    private static final Logger log = LoggerFactory.getLogger(NotificationListener.class);

    /** How long to wait for the matching OrderPlaced when the inventory event arrives first. */
    private static final Duration ORDER_WAIT = Duration.ofSeconds(2);

    /** Latest known content of each order, kept in memory - a notification service needs no database. */
    private final Map<Long, OrderPlaced> orders = new ConcurrentHashMap<>();

    /** Orders we already mailed about, so a re-delivered inventory event sends nothing. */
    private final Set<Long> notified = ConcurrentHashMap.newKeySet();

    @KafkaListener(topics = Topics.ORDER_EVENTS, groupId = "notification-service")
    public void onOrderPlaced(OrderPlaced event) {
        orders.put(event.orderId(), event);
        log.info("OrderPlaced noted: order={} items={} total={}",
                event.orderId(), event.items().size(), event.totalPrice());
    }

    @KafkaListener(topics = Topics.INVENTORY_EVENTS, groupId = "notification-service")
    public void onInventoryEvent(InventoryEvent event) {
        if (!notified.add(event.orderId())) {
            log.info("Order {} already notified - duplicate {} ignored", event.orderId(), event.status());
            return;
        }

        OrderPlaced order = awaitOrder(event.orderId());

        StringBuilder mail = new StringBuilder();
        mail.append("\n================ SIMULATED EMAIL ================\n");
        mail.append("To      : customer of order #").append(event.orderId()).append('\n');
        mail.append("Subject : Your ShopStream order was ")
                .append(event.isReserved() ? "confirmed" : "rejected").append('\n');
        if (order != null) {
            mail.append("Total   : ").append(order.totalPrice()).append('\n');
            mail.append("Items   :\n");
            order.items().forEach(line ->
                    mail.append("          - ").append(line.quantity())
                            .append(" x product ").append(line.productId()).append('\n'));
        } else {
            mail.append("Details : order content not received in time\n");
        }
        if (!event.isReserved() && event.reason() != null) {
            mail.append("Reason  : ").append(event.reason()).append('\n');
        }
        mail.append("=================================================");

        log.info(mail.toString());
    }

    /**
     * The two topics are consumed independently, so the inventory event can be
     * handled before the order event of the same order has been read. Waiting a
     * short, bounded time keeps the mail complete without coupling the service to
     * order-service's HTTP API.
     */
    private OrderPlaced awaitOrder(Long orderId) {
        Instant deadline = Instant.now().plus(ORDER_WAIT);
        OrderPlaced order = orders.get(orderId);
        while (order == null && Instant.now().isBefore(deadline)) {
            try {
                Thread.sleep(50);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
            order = orders.get(orderId);
        }
        return order;
    }
}
