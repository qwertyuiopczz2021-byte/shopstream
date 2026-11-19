package hu.unimiskolc.shopstream.order;

import hu.unimiskolc.shopstream.events.InventoryEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class InventoryListener {

    private static final Logger log = LoggerFactory.getLogger(InventoryListener.class);

    private final OrderService orderService;

    public InventoryListener(OrderService orderService) {
        this.orderService = orderService;
    }

    @KafkaListener(topics = "${shopstream.topics.inventory-events}", groupId = "order-service")
    public void onInventoryEvent(InventoryEvent event) {
        log.info("{} received: order={} reason={}", event.status(), event.orderId(), event.reason());
        orderService.applyInventoryResult(event);
    }
}