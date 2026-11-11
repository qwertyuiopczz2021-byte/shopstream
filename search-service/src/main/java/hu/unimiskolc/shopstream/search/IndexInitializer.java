package hu.unimiskolc.shopstream.search;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.data.elasticsearch.core.ElasticsearchOperations;
import org.springframework.data.elasticsearch.core.IndexOperations;
import org.springframework.stereotype.Component;

/**
 * Creates the products index (and its mapping) on startup if it is not there
 * yet, so that a GET /search on an empty catalogue answers with zero hits
 * instead of failing on a missing index.
 */
@Component
public class IndexInitializer implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(IndexInitializer.class);

    private final ElasticsearchOperations operations;

    public IndexInitializer(ElasticsearchOperations operations) {
        this.operations = operations;
    }

    @Override
    public void run(ApplicationArguments args) {
        IndexOperations index = operations.indexOps(ProductDocument.class);
        if (index.exists()) {
            log.info("Index {} already exists", index.getIndexCoordinates().getIndexName());
            return;
        }
        index.createWithMapping();
        log.info("Created index {} with the explicit mapping", index.getIndexCoordinates().getIndexName());
    }
}
