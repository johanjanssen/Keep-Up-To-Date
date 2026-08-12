package com.example.helloconference;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Hello Conference controller — a simple demo app used by Build Docker Images
 * to test various container optimizations (jlink, native, CRaC, CDS).
 */
@RestController
public class HelloConferenceController {

    private static final Logger log = LoggerFactory.getLogger(HelloConferenceController.class);

    @GetMapping("/hello")
    public String hello() {
        return "Hello, YOW!";
    }

    @GetMapping("/api/products/search")
    public ResponseEntity<Map<String, Object>> searchProducts(@RequestParam String q) {
        log.info("Product search query: {}", q);

        List<Map<String, String>> results = List.of(
                Map.of("id", "1", "name", "Conference T-Shirt", "price", "25.00"),
                Map.of("id", "2", "name", "Speaker Badge", "price", "5.00"),
                Map.of("id", "3", "name", "Workshop Notebook", "price", "12.50")
        );

        List<Map<String, String>> filtered = results.stream()
                .filter(p -> p.get("name").toLowerCase().contains(q.toLowerCase()))
                .collect(Collectors.toList());

        return ResponseEntity.ok(Map.of(
                "query", q,
                "count", filtered.size(),
                "results", filtered
        ));
    }
}
