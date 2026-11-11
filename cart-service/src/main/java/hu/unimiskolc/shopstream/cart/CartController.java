package hu.unimiskolc.shopstream.cart;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/**
 * The cart API. A cart is addressed by userId and kept in Redis, so these
 * handlers are thin: read the hash, change one line, write it back.
 */
@RestController
@RequestMapping("/carts/{userId}")
public class CartController {

    private final CartService carts;

    public CartController(CartService carts) {
        this.carts = carts;
    }

    @GetMapping
    public CartResponse get(@PathVariable String userId) {
        return CartResponse.from(carts.get(userId));
    }

    @PostMapping("/items")
    public CartResponse addItem(@PathVariable String userId, @Valid @RequestBody AddItemRequest request) {
        return CartResponse.from(carts.addItem(userId, request.productId(), request.quantity()));
    }

    @PutMapping("/items/{productId}")
    public CartResponse updateQuantity(@PathVariable String userId,
                                       @PathVariable Long productId,
                                       @Valid @RequestBody UpdateQuantityRequest request) {
        return CartResponse.from(carts.setQuantity(userId, productId, request.quantity()));
    }

    @DeleteMapping("/items/{productId}")
    public CartResponse removeItem(@PathVariable String userId, @PathVariable Long productId) {
        return CartResponse.from(carts.removeItem(userId, productId));
    }

    @DeleteMapping
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void clear(@PathVariable String userId) {
        carts.clear(userId);
    }

    @PostMapping("/checkout")
    public CheckoutResponse checkout(@PathVariable String userId) {
        return carts.checkout(userId);
    }
}
