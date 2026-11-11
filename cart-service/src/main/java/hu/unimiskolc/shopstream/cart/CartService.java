package hu.unimiskolc.shopstream.cart;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.Set;

@Service
public class CartService {

    private static final Logger log = LoggerFactory.getLogger(CartService.class);

    /** The saga ends in one of these two states; anything else is still in flight. */
    private static final Set<String> TERMINAL = Set.of("CONFIRMED", "REJECTED");

    private final CartRepository repository;
    private final OrderClient orderClient;
    private final long timeoutMillis;
    private final long pollIntervalMillis;

    public CartService(CartRepository repository,
                       OrderClient orderClient,
                       @Value("${checkout.timeout-ms}") long timeoutMillis,
                       @Value("${checkout.poll-interval-ms}") long pollIntervalMillis) {
        this.repository = repository;
        this.orderClient = orderClient;
        this.timeoutMillis = timeoutMillis;
        this.pollIntervalMillis = pollIntervalMillis;
    }

    public Cart get(String userId) {
        return repository.findById(userId).orElseGet(() -> new Cart(userId));
    }

    public Cart addItem(String userId, Long productId, int quantity) {
        Cart cart = get(userId);
        cart.add(productId, quantity);
        return repository.save(cart);
    }

    public Cart setQuantity(String userId, Long productId, int quantity) {
        Cart cart = get(userId);
        cart.setQuantity(productId, quantity);
        return repository.save(cart);
    }

    public Cart removeItem(String userId, Long productId) {
        Cart cart = get(userId);
        cart.remove(productId);
        if (cart.isEmpty()) {
            // No empty hashes left behind: an emptied cart simply does not exist.
            repository.deleteById(userId);
            return new Cart(userId);
        }
        return repository.save(cart);
    }

    public Cart clear(String userId) {
        repository.deleteById(userId);
        return new Cart(userId);
    }

    /**
     * Turns the cart into an order and clears the cart only if that order is
     * actually accepted.
     *
     * <p>POST /orders answers PENDING: the stock decision travels the saga
     * (order-events to inventory-events and back), so acceptance is not known
     * yet. We therefore wait a bounded time for the order to reach a terminal
     * state. An order that is rejected — or still pending when we give up —
     * leaves the cart exactly where it was, which is the behaviour the brief
     * asks for and also the only humane one: a failed checkout must not lose
     * the basket.</p>
     */
    public CheckoutResponse checkout(String userId) {
        Cart cart = get(userId);
        if (cart.isEmpty()) {
            throw new IllegalArgumentException("Cart of " + userId + " is empty");
        }

        OrderView placed = orderClient.placeOrder(cart.getItems());
        log.info("Checkout of {} created order {} ({})", userId, placed.id(), placed.status());

        OrderView decided = awaitDecision(placed);

        if ("CONFIRMED".equals(decided.status())) {
            repository.deleteById(userId);
            log.info("Order {} confirmed, cart of {} cleared", decided.id(), userId);
            return new CheckoutResponse(decided.id(), decided.status(), true,
                    "Order confirmed, cart cleared");
        }
        if ("REJECTED".equals(decided.status())) {
            log.info("Order {} rejected, cart of {} kept", decided.id(), userId);
            return new CheckoutResponse(decided.id(), decided.status(), false,
                    "Order rejected, cart kept so the customer can adjust it");
        }
        log.info("Order {} still {} after {} ms, cart of {} kept", decided.id(), decided.status(), timeoutMillis, userId);
        return new CheckoutResponse(decided.id(), decided.status(), false,
                "Order still " + decided.status() + " after " + timeoutMillis + " ms, cart kept");
    }

    private OrderView awaitDecision(OrderView placed) {
        OrderView current = placed;
        long deadline = System.currentTimeMillis() + timeoutMillis;
        while (!TERMINAL.contains(current.status()) && System.currentTimeMillis() < deadline) {
            try {
                Thread.sleep(pollIntervalMillis);
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
                return current;
            }
            current = orderClient.getOrder(placed.id());
        }
        return current;
    }
}
