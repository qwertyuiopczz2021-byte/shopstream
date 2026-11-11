package hu.unimiskolc.shopstream.events;

import java.math.BigDecimal;

/**
 * Published by product-service after a new product has been stored.
 * Message key: productId, so all events of one product land on the same
 * partition and therefore stay in order.
 */
public record ProductCreated(
        Long productId,
        String name,
        String description,
        String category,
        BigDecimal price,
        Integer stock) {
}
