package hu.unimiskolc.shopstream.cart;

/**
 * @param cartCleared true only when the order reached CONFIRMED — a rejected or
 *                    still-pending order leaves the cart untouched, so the user
 *                    does not lose the basket because of a stock problem.
 */
public record CheckoutResponse(Long orderId, String orderStatus, boolean cartCleared, String message) {
}
