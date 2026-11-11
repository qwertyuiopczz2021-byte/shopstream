package hu.unimiskolc.shopstream.cart;

import org.springframework.data.annotation.Id;
import org.springframework.data.redis.core.RedisHash;
import org.springframework.data.redis.core.TimeToLive;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

/**
 * One cart = one Redis hash: key "carts:&lt;userId&gt;", one field per property.
 * The cart lives only in Redis, so cart-service needs no database at all.
 *
 * <p>{@code @TimeToLive} makes Redis expire the whole key, which is the point of
 * storing carts here: an abandoned cart disappears by itself instead of staying
 * in a table forever. The value is seconds (see {@link #TTL_SECONDS}).</p>
 */
@RedisHash("carts")
public class Cart {

    /** Seven days without a change and the cart is gone. */
    public static final long TTL_SECONDS = 7L * 24 * 60 * 60;

    @Id
    private String userId;

    private List<CartItem> items = new ArrayList<>();

    @TimeToLive(unit = TimeUnit.SECONDS)
    private Long ttl = TTL_SECONDS;

    public Cart() {
    }

    public Cart(String userId) {
        this.userId = userId;
    }

    public String getUserId() {
        return userId;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }

    public List<CartItem> getItems() {
        return items;
    }

    public void setItems(List<CartItem> items) {
        this.items = items;
    }

    public Long getTtl() {
        return ttl;
    }

    public void setTtl(Long ttl) {
        this.ttl = ttl;
    }

    /**
     * Adding a product that is already in the cart increases its quantity: a
     * cart has one line per product, not two lines the user has to add up.
     */
    public void add(Long productId, int quantity) {
        find(productId).ifPresentOrElse(
                item -> item.setQuantity(item.getQuantity() + quantity),
                () -> items.add(new CartItem(productId, quantity)));
    }

    public void setQuantity(Long productId, int quantity) {
        CartItem item = find(productId).orElseThrow(() -> new ItemNotFoundException(productId));
        item.setQuantity(quantity);
    }

    public void remove(Long productId) {
        if (!items.removeIf(item -> item.getProductId().equals(productId))) {
            throw new ItemNotFoundException(productId);
        }
    }

    public Optional<CartItem> find(Long productId) {
        return items.stream()
                .filter(item -> item.getProductId().equals(productId))
                .findFirst();
    }

    public boolean isEmpty() {
        return items.isEmpty();
    }

    public int totalQuantity() {
        return items.stream().mapToInt(CartItem::getQuantity).sum();
    }
}
