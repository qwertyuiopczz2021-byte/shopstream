package hu.unimiskolc.shopstream.product;

import hu.unimiskolc.shopstream.events.ProductCreated;
import hu.unimiskolc.shopstream.events.ProductDeleted;
import hu.unimiskolc.shopstream.events.ProductUpdated;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

/**
 * Writes the product-events stream. The message key is always the product id,
 * which is what keeps the created / updated / deleted messages of one product in
 * order: Kafka preserves order inside a partition, and one key means one
 * partition.
 */
@Component
public class ProductEventsPublisher {

    private static final Logger log = LoggerFactory.getLogger(ProductEventsPublisher.class);

    private final KafkaTemplate<Object, Object> kafkaTemplate;
    private final String productEventsTopic;

    public ProductEventsPublisher(KafkaTemplate<Object, Object> kafkaTemplate,
                                 @Value("${shopstream.topics.product-events}") String productEventsTopic) {
        this.kafkaTemplate = kafkaTemplate;
        this.productEventsTopic = productEventsTopic;
    }

    public void created(Product product) {
        send(new ProductCreated(product.getId(), product.getName(), product.getDescription(),
                product.getCategory(), product.getPrice(), product.getStock()));
    }

    public void updated(Product product) {
        send(new ProductUpdated(product.getId(), product.getName(), product.getDescription(),
                product.getCategory(), product.getPrice(), product.getStock()));
    }

    public void deleted(Long productId) {
        send(new ProductDeleted(productId));
    }

    private void send(Object event) {
        Long productId = switch (event) {
            case ProductCreated created -> created.productId();
            case ProductUpdated updated -> updated.productId();
            case ProductDeleted deleted -> deleted.productId();
            default -> throw new IllegalArgumentException("Not a product event: " + event);
        };
        kafkaTemplate.send(productEventsTopic, String.valueOf(productId), event);
        log.info("{} published for product {}", event.getClass().getSimpleName(), productId);
    }
}