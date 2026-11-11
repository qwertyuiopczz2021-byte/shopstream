package hu.unimiskolc.shopstream.search;

import co.elastic.clients.elasticsearch._types.query_dsl.BoolQuery;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.elasticsearch.client.elc.NativeQuery;
import org.springframework.data.elasticsearch.core.ElasticsearchOperations;
import org.springframework.data.elasticsearch.core.SearchHit;
import org.springframework.data.elasticsearch.core.SearchHits;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.math.BigDecimal;
import java.util.List;

/**
 * Builds the query for GET /search. A derived repository method cannot express
 * "text OR text AND category AND price between x and y", so the query is built
 * with the Elasticsearch query DSL and executed through ElasticsearchOperations.
 */
@Service
public class ProductSearchService {

    private static final List<String> FULL_TEXT_FIELDS = List.of("name", "description");
    private static final int MAX_PAGE_SIZE = 100;

    private final ElasticsearchOperations operations;

    public ProductSearchService(ElasticsearchOperations operations) {
        this.operations = operations;
    }

    public SearchResponse search(String text, String category, BigDecimal minPrice, BigDecimal maxPrice,
                                 int page, int size) {
        if (page < 0) {
            throw new IllegalArgumentException("page must be 0 or greater");
        }
        if (size < 1 || size > MAX_PAGE_SIZE) {
            throw new IllegalArgumentException("size must be between 1 and " + MAX_PAGE_SIZE);
        }
        if (minPrice != null && maxPrice != null && minPrice.compareTo(maxPrice) > 0) {
            throw new IllegalArgumentException("minPrice must not be greater than maxPrice");
        }

        BoolQuery.Builder bool = new BoolQuery.Builder();
        if (StringUtils.hasText(text)) {
            bool.must(m -> m.multiMatch(mm -> mm.query(text).fields(FULL_TEXT_FIELDS)));
        }
        if (StringUtils.hasText(category)) {
            bool.filter(f -> f.term(t -> t.field("category").value(category)));
        }
        if (minPrice != null || maxPrice != null) {
            bool.filter(f -> f.range(r -> {
                r.field("price");
                if (minPrice != null) {
                    r.gte(co.elastic.clients.json.JsonData.of(minPrice.doubleValue()));
                }
                if (maxPrice != null) {
                    r.lte(co.elastic.clients.json.JsonData.of(maxPrice.doubleValue()));
                }
                return r;
            }));
        }

        NativeQuery query = NativeQuery.builder()
                .withQuery(bool.build()._toQuery())
                .withPageable(PageRequest.of(page, size))
                .build();

        SearchHits<ProductDocument> hits = operations.search(query, ProductDocument.class);
        List<ProductDocument> items = hits.getSearchHits().stream().map(SearchHit::getContent).toList();
        return new SearchResponse(hits.getTotalHits(), page, size, items);
    }
}