package hu.unimiskolc.shopstream.order;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

/**
 * Declarative HTTP client for product-service.
 *
 * <p>There is no URL in this interface: "product-service" is the name the service
 * registered in Eureka, and Spring Cloud LoadBalancer picks one of its instances
 * for every call. Step 1 used a RestClient with PRODUCT_SERVICE_URL; that
 * environment variable is gone, and with it the only place that had to know an
 * address of another service.</p>
 */
@FeignClient(name = "product-service", path = "/products")
public interface ProductFeignClient {

    @GetMapping("/{id}")
    ProductDto findById(@PathVariable("id") Long productId);
}
