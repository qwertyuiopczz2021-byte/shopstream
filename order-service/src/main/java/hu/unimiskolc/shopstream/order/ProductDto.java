package hu.unimiskolc.shopstream.order;

import java.math.BigDecimal;

/** The part of product-service's response that order-service needs. */
public record ProductDto(Long id, String name, BigDecimal price, Integer stock) {
}
