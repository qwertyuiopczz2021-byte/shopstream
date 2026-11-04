package hu.unimiskolc.shopstream.order;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;

@Service
public class OrderService {

    private final OrderRepository repository;
    private final ProductClient productClient;

    public OrderService(OrderRepository repository, ProductClient productClient) {
        this.repository = repository;
        this.productClient = productClient;
    }

    @Transactional
    public OrderResponse create(CreateOrderRequest request) {
        Order order = new Order();
        order.setStatus(OrderStatus.PENDING);

        BigDecimal total = BigDecimal.ZERO;

        for (CreateOrderRequest.Line line : request.items()) {
            ProductDto product = productClient.findById(line.productId());

            OrderItem item = new OrderItem();
            item.setProductId(product.id());
            item.setQuantity(line.quantity());
            item.setUnitPrice(product.price());
            order.addItem(item);

            total = total.add(product.price().multiply(BigDecimal.valueOf(line.quantity())));
        }

        order.setTotalPrice(total);
        return OrderResponse.from(repository.save(order));
    }

    @Transactional(readOnly = true)
    public OrderResponse findById(Long id) {
        Order order = repository.findById(id)
                .orElseThrow(() -> new NotFoundException("No order with id " + id));
        return OrderResponse.from(order);
    }
}
