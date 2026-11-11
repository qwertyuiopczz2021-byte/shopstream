package hu.unimiskolc.shopstream.cart;

import org.springframework.data.repository.CrudRepository;

/** Spring Data Redis writes this repository against the "carts:" keyspace. */
public interface CartRepository extends CrudRepository<Cart, String> {
}
