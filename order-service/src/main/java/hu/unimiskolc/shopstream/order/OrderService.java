package hu.unimiskolc.shopstream.order;

import hu.unimiskolc.shopstream.events.InventoryEvent;
import hu.unimiskolc.shopstream.events.OrderConfirmed;
import hu.unimiskolc.shopstream.events.OrderPlaced;
import hu.unimiskolc.shopstream.events.OrderRejected;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

@Service
public class OrderService {

    private static final Logger log = LoggerFactory.getLogger(OrderService.class);

    private final OrderRepository repository;
    private final ProductFeignClient productClient;
    private final ApplicationEventPublisher events;

    public OrderService(OrderRepository repository, ProductFeignClient productClient, ApplicationEventPublisher events) {
        this.repository = repository;
        this.productClient = productClient;
        this.events = events;
    }

    @Transactional
    public OrderResponse create(CreateOrderRequest request) {
        Order order = new Order();
        order.setStatus(OrderStatus.PENDING);

        BigDecimal total = BigDecimal.ZERO;
        List<OrderPlaced.Line> lines = new ArrayList<>();

        for (CreateOrderRequest.Line line : request.items()) {
            ProductDto product = productClient.findById(line.productId());

            OrderItem item = new OrderItem();
            item.setProductId(product.id());
            item.setQuantity(line.quantity());
            item.setUnitPrice(product.price());
            order.addItem(item);

            lines.add(new OrderPlaced.Line(product.id(), line.quantity()));
            total = total.add(product.price().multiply(BigDecimal.valueOf(line.quantity())));
        }

        order.setTotalPrice(total);
        Order saved = repository.save(order);

        // Stored as PENDING first: the order only becomes CONFIRMED once
        // product-service reports that the stock was actually reserved.
        events.publishEvent(new OrderPlaced(saved.getId(), lines, saved.getTotalPrice(), saved.getCreatedAt()));

        return OrderResponse.from(saved);
    }

    @Transactional(readOnly = true)
    public OrderResponse findById(Long id) {
        Order order = repository.findById(id)
                .orElseThrow(() -> new NotFoundException("No order with id " + id));
        return OrderResponse.from(order);
    }

    /**
     * Applies the outcome published by product-service and announces the new state
     * on order-events. Safe to call twice with the same event: an order that has
     * already reached a final state keeps it and publishes nothing again.
     */
    @Transactional
    public void applyInventoryResult(InventoryEvent event) {
        Order order = repository.findById(event.orderId()).orElse(null);
        if (order == null) {
            log.warn("InventoryEvent for unknown order {} - ignored", event.orderId());
            return;
        }
        if (order.getStatus() != OrderStatus.PENDING) {
            log.info("Order {} is already {} - duplicate InventoryEvent ignored", order.getId(), order.getStatus());
            return;
        }

        order.setStatus(event.isReserved() ? OrderStatus.CONFIRMED : OrderStatus.REJECTED);
        repository.save(order);
        log.info("Order {} -> {}{}", order.getId(), order.getStatus(),
                event.reason() == null ? "" : " (" + event.reason() + ")");

        if (event.isReserved()) {
            events.publishEvent(OrderConfirmed.now(order.getId(), order.getTotalPrice()));
        } else {
            events.publishEvent(OrderRejected.now(order.getId(), event.reason()));
        }
    }
}