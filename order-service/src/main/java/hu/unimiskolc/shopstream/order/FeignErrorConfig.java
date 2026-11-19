package hu.unimiskolc.shopstream.order;

import feign.Response;
import feign.codec.ErrorDecoder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Turns the two HTTP answers Feign would otherwise rethrow as a FeignException
 * into the exceptions this service already knows how to report: a missing product
 * stays a 404 for the caller, an unreachable or broken product-service becomes a
 * 503.
 *
 * <p>The decoder is a bean, so it applies to every Feign client in this
 * application. Without it the default decoder throws FeignException, which the
 * controller advice would report as a generic 500 - this mapping is what keeps the
 * API's error contract unchanged now that RestClient no longer does it by hand.</p>
 */
@Configuration
public class FeignErrorConfig {

    @Bean
    ErrorDecoder productErrorDecoder() {
        ErrorDecoder defaultDecoder = new ErrorDecoder.Default();

        return (String methodKey, Response response) -> {
            String path = response.request() == null ? methodKey : response.request().url();
            return switch (response.status()) {
                case 404 -> new ProductNotFoundException("product-service has no product at " + path);
                case 500, 502, 503, 504 -> new ProductUnavailableException(
                        "product-service answered " + response.status() + " for " + path);
                default -> defaultDecoder.decode(methodKey, response);
            };
        };
    }
}
