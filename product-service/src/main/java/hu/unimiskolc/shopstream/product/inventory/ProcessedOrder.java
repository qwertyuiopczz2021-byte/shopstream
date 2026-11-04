package hu.unimiskolc.shopstream.product.inventory;

import hu.unimiskolc.shopstream.events.InventoryEvent;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;

/**
 * One row per order that product-service already handled. This is what makes
 * stock reservation idempotent: Kafka delivers at least once, so the same
 * OrderPlaced can arrive twice - after a rebalance or a restart - and the second
 * time the stock must not be decremented again.
 */
@Entity
@Table(name = "processed_orders")
public class ProcessedOrder {

    @Id
    @Column(name = "order_id")
    private Long orderId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private InventoryEvent.Status status;

    @Column(length = 255)
    private String reason;

    @Column(nullable = false)
    private Instant processedAt = Instant.now();

    protected ProcessedOrder() {
    }

    public ProcessedOrder(Long orderId, InventoryEvent.Status status, String reason) {
        this.orderId = orderId;
        this.status = status;
        this.reason = reason;
        this.processedAt = Instant.now();
    }

    public Long getOrderId() {
        return orderId;
    }

    public InventoryEvent.Status getStatus() {
        return status;
    }

    public String getReason() {
        return reason;
    }

    public Instant getProcessedAt() {
        return processedAt;
    }
}
