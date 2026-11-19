package hu.unimiskolc.shopstream.search;

import hu.unimiskolc.shopstream.events.ProductCreated;
import hu.unimiskolc.shopstream.events.ProductDeleted;
import hu.unimiskolc.shopstream.events.ProductUpdated;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

/**
 * Keeps the products index in step with the catalogue. Because the event key is
 * the product id, created / updated / deleted of one product are consumed in the
 * order they were produced, so the last write always wins.
 */
@Component
public class ProductIndexListener {

    private static final Logger log = LoggerFactory.getLogger(ProductIndexListener.class);

    private final ProductSearchRepository repository;

    public ProductIndexListener(ProductSearchRepository repository) {
        this.repository = repository;
    }

    @KafkaListener(topics = "${shopstream.topics.product-events}", groupId = "search-service")
    public void onProductEvent(ConsumerRecord<String, Object> record) {
        Object event = record.value();
        if (event instanceof ProductCreated created) {
            repository.save(ProductDocument.from(created));
            log.info("Indexed new product {}", created.productId());
        } else if (event instanceof ProductUpdated updated) {
            repository.save(ProductDocument.from(updated));
            log.info("Re-indexed product {}", updated.productId());
        } else if (event instanceof ProductDeleted deleted) {
            repository.deleteById(deleted.productId());
            log.info("Removed product {} from the index", deleted.productId());
        } else {
            log.debug("Ignoring {} - not a product event", event == null ? "null" : event.getClass().getSimpleName());
        }
    }
}