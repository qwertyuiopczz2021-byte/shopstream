package hu.unimiskolc.shopstream.search;

import hu.unimiskolc.shopstream.events.ProductCreated;
import hu.unimiskolc.shopstream.events.ProductUpdated;
import org.springframework.data.annotation.Id;
import org.springframework.data.elasticsearch.annotations.Document;
import org.springframework.data.elasticsearch.annotations.Field;
import org.springframework.data.elasticsearch.annotations.FieldType;

/**
 * The searchable copy of a product. The field types are declared explicitly
 * instead of being guessed, because the mapping decides what queries work later:
 * name and description are analysed text (full-text search), category is a
 * keyword (exact filtering), price is a double and stock an integer (range
 * filtering and sorting).
 */
@Document(indexName = "products")
public class ProductDocument {

    @Id
    private Long id;

    @Field(type = FieldType.Text)
    private String name;

    @Field(type = FieldType.Text)
    private String description;

    @Field(type = FieldType.Keyword)
    private String category;

    @Field(type = FieldType.Double)
    private Double price;

    @Field(type = FieldType.Integer)
    private Integer stock;

    public ProductDocument() {
    }

    public static ProductDocument from(ProductCreated event) {
        return of(event.productId(), event.name(), event.description(), event.category(),
                event.price(), event.stock());
    }

    public static ProductDocument from(ProductUpdated event) {
        return of(event.productId(), event.name(), event.description(), event.category(),
                event.price(), event.stock());
    }

    private static ProductDocument of(Long id, String name, String description, String category,
                                      java.math.BigDecimal price, Integer stock) {
        ProductDocument document = new ProductDocument();
        document.id = id;
        document.name = name;
        document.description = description;
        document.category = category;
        document.price = price == null ? null : price.doubleValue();
        document.stock = stock;
        return document;
    }

    public Long getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getDescription() {
        return description;
    }

    public String getCategory() {
        return category;
    }

    public Double getPrice() {
        return price;
    }

    public Integer getStock() {
        return stock;
    }
}
