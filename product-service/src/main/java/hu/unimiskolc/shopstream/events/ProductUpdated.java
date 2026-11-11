package hu.unimiskolc.shopstream.events;

import java.math.BigDecimal;

/**
 * Published by product-service whenever an existing product changes: a normal
 * edit, or a stock reservation made by the order saga.
 * Message key: productId.
 */
public record ProductUpdated(
        Long productId,
        String name,
        String description,
        String category,
        BigDecimal price,
        Integer stock) {
}
