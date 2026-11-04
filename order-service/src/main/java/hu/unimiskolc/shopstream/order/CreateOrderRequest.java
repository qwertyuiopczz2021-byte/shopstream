package hu.unimiskolc.shopstream.order;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

import java.util.List;

public record CreateOrderRequest(
        @NotEmpty(message = "at least one item is required") List<@Valid Line> items) {

    public record Line(
            @NotNull @Positive Long productId,
            @NotNull @Positive Integer quantity) {
    }
}
