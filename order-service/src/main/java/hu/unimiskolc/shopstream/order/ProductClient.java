package hu.unimiskolc.shopstream.order;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/**
 * Calls product-service over HTTP. The base URL comes from the environment
 * (PRODUCT_SERVICE_URL), never from a hard-coded host.
 */
@Component
public class ProductClient {

    private final RestClient restClient;

    public ProductClient(RestClient.Builder builder,
                         @Value("${product.service.url}") String baseUrl) {
        this.restClient = builder.baseUrl(baseUrl).build();
    }

    public ProductDto findById(Long productId) {
        try {
            return restClient.get()
                    .uri("/products/{id}", productId)
                    .retrieve()
                    .body(ProductDto.class);
        } catch (HttpClientErrorException ex) {
            if (ex.getStatusCode() == HttpStatus.NOT_FOUND) {
                throw new ProductNotFoundException("No product with id " + productId);
            }
            throw new ProductUnavailableException("product-service rejected the request", ex);
        } catch (RestClientException ex) {
            throw new ProductUnavailableException("product-service is not reachable", ex);
        }
    }
}
