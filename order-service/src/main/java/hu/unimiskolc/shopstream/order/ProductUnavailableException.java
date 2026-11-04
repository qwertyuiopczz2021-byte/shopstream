package hu.unimiskolc.shopstream.order;

public class ProductUnavailableException extends RuntimeException {
    public ProductUnavailableException(String message, Throwable cause) {
        super(message, cause);
    }
}
