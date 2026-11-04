package hu.unimiskolc.shopstream.events;

import java.time.Instant;

/**
 * Published by product-service after it tried to reserve stock for an order.
 * {@link Status#STOCK_RESERVED} corresponds to the StockReserved event and
 * {@link Status#STOCK_REJECTED} to StockRejected.
 * Message key: orderId.
 */
public record InventoryEvent(
        Long orderId,
        Status status,
        String reason,
        Instant occurredAt) {

    public enum Status {
        STOCK_RESERVED,
        STOCK_REJECTED
    }

    public static InventoryEvent reserved(Long orderId) {
        return new InventoryEvent(orderId, Status.STOCK_RESERVED, null, Instant.now());
    }

    public static InventoryEvent rejected(Long orderId, String reason) {
        return new InventoryEvent(orderId, Status.STOCK_REJECTED, reason, Instant.now());
    }

    public boolean isReserved() {
        return status == Status.STOCK_RESERVED;
    }
}
