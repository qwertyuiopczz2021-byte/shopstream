package hu.unimiskolc.shopstream.cart;

import java.util.List;

/** The body order-service expects on POST /orders. */
public record OrderRequest(List<Line> items) {

    public record Line(Long productId, int quantity) {
    }
}
