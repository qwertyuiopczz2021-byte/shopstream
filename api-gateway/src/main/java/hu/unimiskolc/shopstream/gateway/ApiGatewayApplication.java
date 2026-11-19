package hu.unimiskolc.shopstream.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * The only container that publishes a port. Everything the browser asks for
 * arrives here first and is routed by path to one of the services behind it,
 * which are found through Eureka, never by a fixed address.
 */
@SpringBootApplication
public class ApiGatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(ApiGatewayApplication.class, args);
    }
}
