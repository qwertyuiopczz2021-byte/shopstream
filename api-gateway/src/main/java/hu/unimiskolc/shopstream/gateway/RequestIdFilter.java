package hu.unimiskolc.shopstream.gateway;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.UUID;

/**
 * Runs for every request that passes through the gateway, whatever the route.
 *
 * <p>A request that arrives without an X-Request-Id gets one; a request that
 * already carries one keeps it, so a caller can follow its own id through the
 * system. The id is echoed on the response and written to the log together with
 * the method, the path and how long the call took, which makes one line in this
 * log enough to find the request in the logs of the service behind it.
 */
@Component
public class RequestIdFilter implements GlobalFilter, Ordered {

    public static final String HEADER = "X-Request-Id";

    private static final Logger log = LoggerFactory.getLogger(RequestIdFilter.class);

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String incoming = exchange.getRequest().getHeaders().getFirst(HEADER);
        String requestId = (incoming == null || incoming.isBlank())
                ? UUID.randomUUID().toString()
                : incoming;

        ServerHttpRequest request = exchange.getRequest().mutate()
                .header(HEADER, requestId)
                .build();
        ServerHttpResponse response = exchange.getResponse();
        response.getHeaders().set(HEADER, requestId);

        String method = request.getMethod().name();
        String path = request.getURI().getPath();
        long started = System.nanoTime();

        return chain.filter(exchange.mutate().request(request).build())
                .doOnSuccess(ignored -> log.info("{} {} -> {} ({} ms) requestId={}",
                        method, path, status(response), elapsedMs(started), requestId))
                .doOnError(error -> log.warn("{} {} -> failed after {} ms requestId={} reason={}",
                        method, path, elapsedMs(started), requestId, error.toString()));
    }

    private static String status(ServerHttpResponse response) {
        return response.getStatusCode() == null ? "no status" : response.getStatusCode().toString();
    }

    private static long elapsedMs(long started) {
        return (System.nanoTime() - started) / 1_000_000;
    }

    /**
     * Ordered.HIGHEST_PRECEDENCE so the id is set before anything else can log.
     */
    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;
    }
}
