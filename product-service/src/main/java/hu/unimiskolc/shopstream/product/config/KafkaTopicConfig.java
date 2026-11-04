package hu.unimiskolc.shopstream.product.config;

import hu.unimiskolc.shopstream.events.Topics;
import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

/**
 * Declares the topics this service relies on. Spring Boot's KafkaAdmin creates
 * them on startup if they do not exist; the broker itself is configured with
 * automatic topic creation turned off, so the partition count is always ours and
 * never the broker default of one.
 */
@Configuration
public class KafkaTopicConfig {

    private static final int PARTITIONS = 3;
    private static final int REPLICAS = 1;

    @Bean
    NewTopic orderEvents() {
        return TopicBuilder.name(Topics.ORDER_EVENTS).partitions(PARTITIONS).replicas(REPLICAS).build();
    }

    @Bean
    NewTopic inventoryEvents() {
        return TopicBuilder.name(Topics.INVENTORY_EVENTS).partitions(PARTITIONS).replicas(REPLICAS).build();
    }

    @Bean
    NewTopic productEvents() {
        return TopicBuilder.name(Topics.PRODUCT_EVENTS).partitions(PARTITIONS).replicas(REPLICAS).build();
    }
}
