package hu.unimiskolc.shopstream.order.config;

import hu.unimiskolc.shopstream.events.Topics;
import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

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
}
