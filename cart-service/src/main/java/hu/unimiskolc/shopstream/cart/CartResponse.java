package hu.unimiskolc.shopstream.cart;

import java.util.List;

public record CartResponse(String userId, List<Line> items, int totalQuantity) {

    public record Line(Long productId, int quantity) {
    }

    public static CartResponse from(Cart cart) {
        List<Line> lines = cart.getItems().stream()
                .map(item -> new Line(item.getProductId(), item.getQuantity()))
                .toList();
        return new CartResponse(cart.getUserId(), lines, cart.totalQuantity());
    }
}
