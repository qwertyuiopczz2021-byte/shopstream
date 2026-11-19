package hu.unimiskolc.shopstream.cart;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

import java.util.List;

/**
 * Declarative HTTP client for order-service, found through Eureka by name.
 *
 * <p>Step 4 used a RestClient whose base URL came from ORDER_SERVICE_URL. The
 * interface below is what replaced it: two method signatures that mirror the two
 * endpoints, no address anywhere.</p>
 */
@FeignClient(name = "order-service", path = "/orders")
public interface OrderClient {

    @PostMapping
    OrderView placeOrder(@RequestBody OrderRequest request);

    @GetMapping("/{id}")
    OrderView getOrder(@PathVariable("id") Long orderId);

    /** Convenience overload so the checkout code does not build the body itself. */
    default OrderView placeOrder(List<CartItem> items) {
        return placeOrder(new OrderRequest(items.stream()
                .map(item -> new OrderRequest.Line(item.getProductId(), item.getQuantity()))
                .toList()));
    }
}
