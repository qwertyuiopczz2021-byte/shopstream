package hu.unimiskolc.shopstream.events;

import java.math.BigDecimal;
import java.time.Instant;

/**
 * Published by order-service on order-events once product-service confirmed that
 * the stock was reserved. This is the event that turns a PENDING order into a
 * final CONFIRMED one.
 * Message key: orderId.
 */
public record OrderConfirmed(Long orderId, BigDecimal totalPrice, Instant confirmedAt) {

    public static OrderConfirmed now(Long orderId, BigDecimal totalPrice) {
        return new OrderConfirmed(orderId, totalPrice, Instant.now());
    }
}
