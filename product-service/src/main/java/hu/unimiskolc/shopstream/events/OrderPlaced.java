package hu.unimiskolc.shopstream.events;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

/**
 * Published by order-service when a customer places an order.
 * Message key: orderId, so all events of one order land on the same partition.
 */
public record OrderPlaced(
        Long orderId,
        List<Line> items,
        BigDecimal totalPrice,
        Instant placedAt) {

    public record Line(Long productId, Integer quantity) {
    }
}
