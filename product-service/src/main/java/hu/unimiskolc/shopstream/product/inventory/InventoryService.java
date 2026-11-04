package hu.unimiskolc.shopstream.product.inventory;

import hu.unimiskolc.shopstream.events.InventoryEvent;
import hu.unimiskolc.shopstream.events.OrderPlaced;
import hu.unimiskolc.shopstream.product.Product;
import hu.unimiskolc.shopstream.product.ProductRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.LinkedHashMap;
import java.util.Map;

@Service
public class InventoryService {

    private static final Logger log = LoggerFactory.getLogger(InventoryService.class);

    private final ProductRepository products;
    private final ProcessedOrderRepository processedOrders;

    public InventoryService(ProductRepository products, ProcessedOrderRepository processedOrders) {
        this.products = products;
        this.processedOrders = processedOrders;
    }

    /**
     * Reserves stock for every line of the order, or for none of it, inside a
     * single database transaction. Returns the event that has to be published once
     * the transaction has committed. A duplicate delivery returns the outcome that
     * was stored the first time and touches no stock.
     */
    @Transactional
    public InventoryEvent reserve(OrderPlaced order) {
        InventoryEvent previous = processedOrders.findById(order.orderId())
                .map(p -> new InventoryEvent(order.orderId(), p.getStatus(), p.getReason(), p.getProcessedAt()))
                .orElse(null);
        if (previous != null) {
            log.info("Order {} was already processed as {} - stock untouched (idempotent delivery)",
                    order.orderId(), previous.status());
            return previous;
        }

        Map<Long, Integer> wanted = new LinkedHashMap<>();
        for (OrderPlaced.Line line : order.items()) {
            wanted.merge(line.productId(), line.quantity(), Integer::sum);
        }

        Map<Long, Product> loaded = new LinkedHashMap<>();
        for (Map.Entry<Long, Integer> entry : wanted.entrySet()) {
            Long productId = entry.getKey();
            Integer quantity = entry.getValue();
            Product product = products.findById(productId).orElse(null);
            if (product == null) {
                return reject(order.orderId(), "Unknown product " + productId);
            }
            if (product.getStock() < quantity) {
                return reject(order.orderId(), "Insufficient stock for product " + productId
                        + ": requested " + quantity + ", available " + product.getStock());
            }
            loaded.put(productId, product);
        }

        wanted.forEach((productId, quantity) ->
                loaded.get(productId).setStock(loaded.get(productId).getStock() - quantity));
        products.saveAll(loaded.values());

        processedOrders.save(new ProcessedOrder(order.orderId(), InventoryEvent.Status.STOCK_RESERVED, null));
        return InventoryEvent.reserved(order.orderId());
    }

    private InventoryEvent reject(Long orderId, String reason) {
        processedOrders.save(new ProcessedOrder(orderId, InventoryEvent.Status.STOCK_REJECTED, reason));
        return InventoryEvent.rejected(orderId, reason);
    }
}
