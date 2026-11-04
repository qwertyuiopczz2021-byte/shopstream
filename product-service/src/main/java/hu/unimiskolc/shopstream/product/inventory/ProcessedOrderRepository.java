package hu.unimiskolc.shopstream.product.inventory;

import org.springframework.data.jpa.repository.JpaRepository;

public interface ProcessedOrderRepository extends JpaRepository<ProcessedOrder, Long> {
}
