package hu.unimiskolc.shopstream.product.inventory;

import hu.unimiskolc.shopstream.events.InventoryEvent;
import hu.unimiskolc.shopstream.events.OrderPlaced;
import hu.unimiskolc.shopstream.events.Topics;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
public class OrderEventListener {

    private static final Logger log = LoggerFactory.getLogger(OrderEventListener.class);

    private final InventoryService inventoryService;
    private final KafkaTemplate<Object, Object> kafkaTemplate;

    public OrderEventListener(InventoryService inventoryService, KafkaTemplate<Object, Object> kafkaTemplate) {
        this.inventoryService = inventoryService;
        this.kafkaTemplate = kafkaTemplate;
    }

    /**
     * order-events carries OrderPlaced, OrderConfirmed and OrderRejected, so the
     * listener takes the whole record and inspects its value: the JSON type header
     * decides which of the three records the deserializer built. Only OrderPlaced
     * concerns the stock; the other two are this service's own answers and are
     * ignored here.
     */
    @KafkaListener(topics = Topics.ORDER_EVENTS, groupId = "product-service")
    public void onOrderEvent(ConsumerRecord<String, Object> record) {
        Object event = record.value();
        if (!(event instanceof OrderPlaced placed)) {
            log.debug("Ignoring {} - not an OrderPlaced", event == null ? "null" : event.getClass().getSimpleName());
            return;
        }

        log.info("OrderPlaced received: order={} lines={}", placed.orderId(), placed.items().size());

        // reserve() is transactional and returns only after the stock change has
        // been committed, so we never publish a result for work that rolled back.
        InventoryEvent result = inventoryService.reserve(placed);

        kafkaTemplate.send(Topics.INVENTORY_EVENTS, String.valueOf(placed.orderId()), result);
        log.info("{} published: order={} reason={}", result.status(), placed.orderId(), result.reason());
    }
}
