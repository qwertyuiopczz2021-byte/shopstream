package hu.unimiskolc.shopstream.order;

import hu.unimiskolc.shopstream.events.OrderPlaced;
import hu.unimiskolc.shopstream.events.Topics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

/**
 * Sends OrderPlaced to Kafka only after the database transaction that stored the
 * order has committed. Publishing inside the transaction would be faster but
 * could announce an order that then gets rolled back.
 */
@Component
public class OrderPlacedPublisher {

    private static final Logger log = LoggerFactory.getLogger(OrderPlacedPublisher.class);

    private final KafkaTemplate<Object, Object> kafkaTemplate;

    public OrderPlacedPublisher(KafkaTemplate<Object, Object> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void publish(OrderPlaced event) {
        kafkaTemplate.send(Topics.ORDER_EVENTS, String.valueOf(event.orderId()), event)
                .whenComplete((result, ex) -> {
                    if (ex != null) {
                        log.error("Could not publish OrderPlaced for order {}", event.orderId(), ex);
                    } else {
                        log.info("OrderPlaced published: order={} partition={} offset={}",
                                event.orderId(),
                                result.getRecordMetadata().partition(),
                                result.getRecordMetadata().offset());
                    }
                });
    }
}
