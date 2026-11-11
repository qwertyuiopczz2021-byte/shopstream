package hu.unimiskolc.shopstream.cart;

public class ItemNotFoundException extends RuntimeException {

    public ItemNotFoundException(Long productId) {
        super("Product " + productId + " is not in this cart");
    }
}
