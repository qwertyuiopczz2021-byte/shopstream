package hu.unimiskolc.shopstream.config;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.config.server.EnableConfigServer;

/**
 * Serves the configuration of every service from one place. The files live in
 * the config-repo folder of this repository, which is mounted into the container;
 * nothing here is read from the local jar, so a change to a yml only needs a
 * restart of the client service, not a rebuild.
 */
@SpringBootApplication
@EnableConfigServer
public class ConfigServerApplication {

    public static void main(String[] args) {
        SpringApplication.run(ConfigServerApplication.class, args);
    }
}
