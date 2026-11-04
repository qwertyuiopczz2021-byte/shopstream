package hu.unimiskolc.shopstream.events;

import java.time.Instant;

/**
 * Published by order-service on order-events when the stock could not be
 * reserved. {@code reason} is the explanation product-service gave.
 * Message key: orderId.
 */
public record OrderRejected(Long orderId, String reason, Instant rejectedAt) {

    public static OrderRejected now(Long orderId, String reason) {
        return new OrderRejected(orderId, reason, Instant.now());
    }
}
