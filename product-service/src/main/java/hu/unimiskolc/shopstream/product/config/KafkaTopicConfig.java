package hu.unimiskolc.shopstream.product.config;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

/**
 * Declares the topics this service relies on. Spring Boot's KafkaAdmin creates
 * them on startup if they do not exist; the broker itself is configured with
 * automatic topic creation turned off, so the partition count is always ours and
 * never the broker default of one.
 *
 * <p>The names and the partition count are no longer constants in Java: they are
 * read from config-server (see config-repo/application.yml under
 * shopstream.topics), so renaming a topic is a configuration change.</p>
 */
@Configuration
public class KafkaTopicConfig {

    private final String orderEvents;
    private final String inventoryEvents;
    private final String productEvents;
    private final int partitions;
    private final int replicas;

    public KafkaTopicConfig(@Value("${shopstream.topics.order-events}") String orderEvents,
                            @Value("${shopstream.topics.inventory-events}") String inventoryEvents,
                            @Value("${shopstream.topics.product-events}") String productEvents,
                            @Value("${shopstream.topics.partitions}") int partitions,
                            @Value("${shopstream.topics.replicas}") int replicas) {
        this.orderEvents = orderEvents;
        this.inventoryEvents = inventoryEvents;
        this.productEvents = productEvents;
        this.partitions = partitions;
        this.replicas = replicas;
    }

    @Bean
    NewTopic orderEventsTopic() {
        return TopicBuilder.name(orderEvents).partitions(partitions).replicas(replicas).build();
    }

    @Bean
    NewTopic inventoryEventsTopic() {
        return TopicBuilder.name(inventoryEvents).partitions(partitions).replicas(replicas).build();
    }

    @Bean
    NewTopic productEventsTopic() {
        return TopicBuilder.name(productEvents).partitions(partitions).replicas(replicas).build();
    }
}
