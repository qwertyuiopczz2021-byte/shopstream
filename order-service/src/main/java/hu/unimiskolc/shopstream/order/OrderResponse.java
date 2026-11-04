package hu.unimiskolc.shopstream.order;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public record OrderResponse(
        Long id,
        OrderStatus status,
        BigDecimal totalPrice,
        Instant createdAt,
        List<Item> items) {

    public record Item(Long productId, Integer quantity, BigDecimal unitPrice) {
    }

    public static OrderResponse from(Order order) {
        List<Item> items = order.getItems().stream()
                .map(item -> new Item(item.getProductId(), item.getQuantity(), item.getUnitPrice()))
                .toList();
        return new OrderResponse(
                order.getId(),
                order.getStatus(),
                order.getTotalPrice(),
                order.getCreatedAt(),
                items);
    }
}
