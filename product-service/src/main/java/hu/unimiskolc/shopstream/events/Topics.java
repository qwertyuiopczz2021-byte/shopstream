package hu.unimiskolc.shopstream.events;

/**
 * Names of the Kafka topics used across the system. Every service carries an
 * identical copy of this contract package so that the JSON type headers written
 * by the producer can be resolved by every consumer.
 */
public final class Topics {

    public static final String ORDER_EVENTS = "order-events";
    public static final String INVENTORY_EVENTS = "inventory-events";
    public static final String PRODUCT_EVENTS = "product-events";

    private Topics() {
    }
}
