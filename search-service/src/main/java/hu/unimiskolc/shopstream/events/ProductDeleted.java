package hu.unimiskolc.shopstream.events;

/**
 * Published by product-service after a product has been removed.
 * Message key: productId.
 */
public record ProductDeleted(Long productId) {
}
