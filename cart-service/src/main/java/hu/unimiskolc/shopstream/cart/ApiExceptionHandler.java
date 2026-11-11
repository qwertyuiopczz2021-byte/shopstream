package hu.unimiskolc.shopstream.cart;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClientResponseException;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(ItemNotFoundException.class)
    public ProblemDetail notFound(ItemNotFoundException exception) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, exception.getMessage());
        problem.setTitle("Item not found");
        return problem;
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ProblemDetail badRequest(IllegalArgumentException exception) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, exception.getMessage());
        problem.setTitle("Invalid cart request");
        return problem;
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ProblemDetail invalidBody(MethodArgumentNotValidException exception) {
        String detail = exception.getBindingResult().getFieldErrors().stream()
                .map(error -> error.getField() + " " + error.getDefaultMessage())
                .sorted()
                .reduce((left, right) -> left + "; " + right)
                .orElse("Invalid request body");
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, detail);
        problem.setTitle("Validation failed");
        return problem;
    }

    /**
     * order-service answered with an error (unknown product, bad line...). We
     * pass the failure on instead of pretending the checkout worked, and the
     * cart stays untouched because nothing was deleted.
     */
    @ExceptionHandler(RestClientResponseException.class)
    public ProblemDetail orderServiceRejected(RestClientResponseException exception) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_GATEWAY,
                "order-service answered " + exception.getStatusCode().value() + ": " + exception.getResponseBodyAsString());
        problem.setTitle("Checkout failed");
        return problem;
    }

    @ExceptionHandler(ResourceAccessException.class)
    public ProblemDetail orderServiceUnreachable(ResourceAccessException exception) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.SERVICE_UNAVAILABLE,
                "order-service is unreachable: " + exception.getMessage());
        problem.setTitle("Checkout failed");
        return problem;
    }
}
