package hu.unimiskolc.shopstream.product;

import jakarta.validation.Valid;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
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

import java.util.List;

/**
 * CRUD over the product catalogue. Every write also goes out on product-events,
 * so that the search index and any other consumer can follow the catalogue
 * without reading this service's database.
 */
@RestController
@RequestMapping("/products")
public class ProductController {

    private final ProductRepository repository;
    private final ProductEventsPublisher events;

    public ProductController(ProductRepository repository, ProductEventsPublisher events) {
        this.repository = repository;
        this.events = events;
    }

    @GetMapping
    public List<Product> list() {
        return repository.findAll();
    }

    /**
     * Cache-aside: the first read of a product loads it from MySQL, later reads
     * come from Redis. The entry is dropped the moment the product changes (here
     * and in the inventory listener), so the cache can never serve a stale price
     * or a stock level that was already sold.
     */
    @GetMapping("/{id}")
    @Cacheable(cacheNames = "products", key = "#id")
    public Product get(@PathVariable Long id) {
        return repository.findById(id)
                .orElseThrow(() -> new NotFoundException("No product with id " + id));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Product create(@Valid @RequestBody ProductRequest request) {
        Product product = new Product();
        apply(product, request);
        Product saved = repository.save(product);
        events.created(saved);
        return saved;
    }

    @PutMapping("/{id}")
    @CacheEvict(cacheNames = "products", key = "#id")
    public Product update(@PathVariable Long id, @Valid @RequestBody ProductRequest request) {
        Product product = repository.findById(id)
                .orElseThrow(() -> new NotFoundException("No product with id " + id));
        apply(product, request);
        Product saved = repository.save(product);
        events.updated(saved);
        return saved;
    }

    @DeleteMapping("/{id}")
    @CacheEvict(cacheNames = "products", key = "#id")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable Long id) {
        if (!repository.existsById(id)) {
            throw new NotFoundException("No product with id " + id);
        }
        repository.deleteById(id);
        events.deleted(id);
    }

    private void apply(Product product, ProductRequest request) {
        product.setName(request.name());
        product.setDescription(request.description());
        product.setCategory(request.category());
        product.setPrice(request.price());
        product.setStock(request.stock());
    }
}