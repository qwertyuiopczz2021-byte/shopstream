package hu.unimiskolc.shopstream.notification;

import hu.unimiskolc.shopstream.events.InventoryEvent;
import hu.unimiskolc.shopstream.events.OrderConfirmed;
import hu.unimiskolc.shopstream.events.OrderPlaced;
import hu.unimiskolc.shopstream.events.OrderRejected;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Stands in for the mail server: it listens to both topics and writes one
 * "email" to the log for every order that reached a final state.
 *
 * The mail is triggered by the order events (OrderConfirmed / OrderRejected),
 * because those are the events that state the final status of an order. Both they
 * and the OrderPlaced event that carries the order content share the order id as
 * the key, so they arrive on the same partition, in order, on the same consumer -
 * the order content is always known before its final status arrives.
 *
 * inventory-events are consumed as well: they carry the stock decision itself and
 * are logged, which makes both halves of the saga visible side by side.
 */
@Component
public class NotificationListener {

    private static final Logger log = LoggerFactory.getLogger(NotificationListener.class);

    /** Latest known content of each order, kept in memory - a notification service needs no database. */
    private final Map<Long, OrderPlaced> orders = new ConcurrentHashMap<>();

    /** Orders we already mailed about, so a re-delivered event sends nothing. */
    private final Set<Long> notified = ConcurrentHashMap.newKeySet();

    /**
     * order-events carries three record types, so the listener takes the whole
     * record and switches on its value; the JSON type header decides which of the
     * three records arrives.
     */
    @KafkaListener(topics = "${shopstream.topics.order-events}", groupId = "notification-service")
    public void onOrderEvent(ConsumerRecord<String, Object> record) {
        switch (record.value()) {
            case OrderPlaced placed -> {
                orders.put(placed.orderId(), placed);
                log.info("OrderPlaced noted: order={} items={} total={}",
                        placed.orderId(), placed.items().size(), placed.totalPrice());
            }
            case OrderConfirmed confirmed -> sendMail(confirmed.orderId(), true, null, confirmed.totalPrice());
            case OrderRejected rejected -> sendMail(rejected.orderId(), false, rejected.reason(), null);
            default -> log.debug("Ignoring {} on order-events", String.valueOf(record.value()));
        }
    }

    @KafkaListener(topics = "${shopstream.topics.inventory-events}", groupId = "notification-service")
    public void onInventoryEvent(InventoryEvent event) {
        log.info("Stock decision for order {}: {}{}", event.orderId(), event.status(),
                event.reason() == null ? "" : " (" + event.reason() + ")");
    }

    private void sendMail(Long orderId, boolean confirmed, String reason, BigDecimal eventTotal) {
        if (!notified.add(orderId)) {
            log.info("Order {} already notified - duplicate final event ignored", orderId);
            return;
        }

        OrderPlaced order = orders.get(orderId);
        BigDecimal total = order != null ? order.totalPrice() : eventTotal;

        StringBuilder mail = new StringBuilder();
        mail.append("\n================ SIMULATED EMAIL ================\n");
        mail.append("To      : customer of order #").append(orderId).append('\n');
        mail.append("Subject : Your ShopStream order was ")
                .append(confirmed ? "confirmed" : "rejected").append('\n');
        if (total != null) {
            mail.append("Total   : ").append(total).append('\n');
        }
        if (order != null) {
            mail.append("Items   :\n");
            order.items().forEach(line ->
                    mail.append("          - ").append(line.quantity())
                            .append(" x product ").append(line.productId()).append('\n'));
        } else {
            mail.append("Details : order content not received\n");
        }
        if (!confirmed && reason != null) {
            mail.append("Reason  : ").append(reason).append('\n');
        }
        mail.append("=================================================");

        log.info(mail.toString());
    }
}