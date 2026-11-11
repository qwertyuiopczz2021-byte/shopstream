package hu.unimiskolc.shopstream.search;

import java.util.List;

public record SearchResponse(long total, int page, int size, List<ProductDocument> items) {
}
