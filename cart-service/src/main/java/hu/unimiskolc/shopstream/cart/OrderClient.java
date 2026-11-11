package hu.unimiskolc.shopstream.cart;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;

/**
 * The only thing cart-service knows about order-service is its URL and two
 * endpoints. Step 5 replaces this class with a {@code @FeignClient} that
 * resolves the host through Eureka; until then the address comes from an
 * environment variable like every other address in the project.
 */
@Component
public class OrderClient {

    private final RestClient restClient;

    public OrderClient(@Value("${order.service.url}") String baseUrl) {
        this.restClient = RestClient.builder().baseUrl(baseUrl).build();
    }

    public OrderView placeOrder(List<CartItem> items) {
        List<Map<String, Object>> lines = items.stream()
                .map(item -> Map.<String, Object>of(
                        "productId", item.getProductId(),
                        "quantity", item.getQuantity()))
                .toList();

        return restClient.post()
                .uri("/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .body(Map.of("items", lines))
                .retrieve()
                .body(OrderView.class);
    }

    public OrderView getOrder(Long orderId) {
        return restClient.get()
                .uri("/orders/{id}", orderId)
                .retrieve()
                .body(OrderView.class);
    }
}
