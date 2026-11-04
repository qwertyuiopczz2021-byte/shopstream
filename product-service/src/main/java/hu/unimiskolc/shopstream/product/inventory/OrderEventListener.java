package hu.unimiskolc.shopstream.product.inventory;

import hu.unimiskolc.shopstream.events.InventoryEvent;
import hu.unimiskolc.shopstream.events.OrderPlaced;
import hu.unimiskolc.shopstream.events.Topics;
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

    @KafkaListener(topics = Topics.ORDER_EVENTS, groupId = "product-service")
    public void onOrderPlaced(OrderPlaced event) {
        log.info("OrderPlaced received: order={} lines={}", event.orderId(), event.items().size());

        // reserve() is transactional and returns only after the stock change has
        // been committed, so we never publish a result for work that rolled back.
        InventoryEvent result = inventoryService.reserve(event);

        kafkaTemplate.send(Topics.INVENTORY_EVENTS, String.valueOf(event.orderId()), result);
        log.info("{} published: order={} reason={}", result.status(), event.orderId(), result.reason());
    }
}
