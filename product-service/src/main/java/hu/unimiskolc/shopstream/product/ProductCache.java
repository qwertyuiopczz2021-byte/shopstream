package hu.unimiskolc.shopstream.product;

import org.springframework.cache.annotation.CacheEvict;
import org.springframework.stereotype.Component;

/**
 * Eviction is its own bean on purpose: an @CacheEvict method called from another
 * method of the same class would bypass the Spring proxy and silently do
 * nothing. Callers here are the write endpoints and the inventory listener.
 */
@Component
public class ProductCache {

    @CacheEvict(cacheNames = "products", key = "#id")
    public void evict(Long id) {
        // the annotation does the work
    }
}
