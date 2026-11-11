package hu.unimiskolc.shopstream.cart;

/** The two fields of an order that a checkout cares about. Unknown fields are ignored. */
public record OrderView(Long id, String status) {
}
