package hu.unimiskolc.shopstream.order.config;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

/**
 * Declares the two topics order-service writes to. The names come from
 * config-server (shopstream.topics.*), so they are shared with the other
 * services instead of being copied into a constant class per service.
 */
@Configuration
public class KafkaTopicConfig {

    private final String orderEvents;
    private final String inventoryEvents;
    private final int partitions;
    private final int replicas;

    public KafkaTopicConfig(@Value("${shopstream.topics.order-events}") String orderEvents,
                            @Value("${shopstream.topics.inventory-events}") String inventoryEvents,
                            @Value("${shopstream.topics.partitions}") int partitions,
                            @Value("${shopstream.topics.replicas}") int replicas) {
        this.orderEvents = orderEvents;
        this.inventoryEvents = inventoryEvents;
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
}
