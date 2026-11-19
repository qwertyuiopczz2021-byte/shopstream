package hu.unimiskolc.shopstream.order;

import hu.unimiskolc.shopstream.events.OrderConfirmed;
import hu.unimiskolc.shopstream.events.OrderPlaced;
import hu.unimiskolc.shopstream.events.OrderRejected;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

/**
 * The single place where order-service writes to order-events.
 *
 * All three events are sent only after the transaction that changed the order has
 * committed: publishing inside the transaction could announce an order that is
 * then rolled back. All three use the order id as the message key, so they land on
 * the same partition and the consumers see them in the order they happened.
 */
@Component
public class OrderEventsPublisher {

    private static final Logger log = LoggerFactory.getLogger(OrderEventsPublisher.class);

    private final KafkaTemplate<Object, Object> kafkaTemplate;
    private final String orderEventsTopic;

    public OrderEventsPublisher(KafkaTemplate<Object, Object> kafkaTemplate,
                                @Value("${shopstream.topics.order-events}") String orderEventsTopic) {
        this.kafkaTemplate = kafkaTemplate;
        this.orderEventsTopic = orderEventsTopic;
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void publish(OrderPlaced event) {
        send("OrderPlaced", event.orderId(), event);
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void publish(OrderConfirmed event) {
        send("OrderConfirmed", event.orderId(), event);
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void publish(OrderRejected event) {
        send("OrderRejected", event.orderId(), event);
    }

    private void send(String type, Long orderId, Object event) {
        kafkaTemplate.send(orderEventsTopic, String.valueOf(orderId), event)
                .whenComplete((result, ex) -> {
                    if (ex != null) {
                        log.error("Could not publish {} for order {}", type, orderId, ex);
                    } else {
                        log.info("{} published: order={} partition={} offset={}",
                                type, orderId,
                                result.getRecordMetadata().partition(),
                                result.getRecordMetadata().offset());
                    }
                });
    }
}