package com.example.helloconference;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * ⚠️  INTENTIONALLY VULNERABLE CONTROLLER — FOR DEMO PURPOSES ONLY  ⚠️
 *
 * All endpoints look like normal business logic. The vulnerabilities are
 * invisible in the code — they come from the dependencies.
 */
@RestController
public class HelloConferenceController {

    // ⚠️ Using Log4j 2.14.1 directly — vulnerable to Log4Shell (CVE-2021-44228)
    private static final Logger log = LogManager.getLogger(HelloConferenceController.class);

    // ⚠️ Jackson 2.9.10 with default typing — vulnerable to deserialization RCE
    @SuppressWarnings("deprecation")
    private static final ObjectMapper unsafeMapper = new ObjectMapper() {{
        enableDefaultTyping();  // CVE-2019-14379 — allows polymorphic deserialization
    }};

    @GetMapping("/hello")
    public String hello() {
        return "Hello, YOW!";
    }

    // ─────────────────────────────────────────────────────────────────
    // DEMO 1 — Log4Shell  (CVE-2021-44228)
    // ─────────────────────────────────────────────────────────────────
    // A perfectly normal product search endpoint. The developer just
    // logs user input — standard practice. The vulnerability is entirely
    // in log4j-core 2.14.1 which interprets JNDI lookup expressions.
    // ─────────────────────────────────────────────────────────────────
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

    // ─────────────────────────────────────────────────────────────────
    // DEMO 2 — Jackson Deserialization RCE  (CVE-2019-14379 and others)
    // ─────────────────────────────────────────────────────────────────
    // Normal "import user profile" API. The ObjectMapper uses
    // enableDefaultTyping() — a common legacy configuration. Attacker
    // embeds class names in JSON to instantiate arbitrary Java objects.
    // ─────────────────────────────────────────────────────────────────
    @PostMapping("/api/users/import")
    public ResponseEntity<Map<String, Object>> importUser(@RequestBody String json) {
        try {
            log.info("Importing user profile");
            JsonNode node = unsafeMapper.readTree(json);
            Object parsed = unsafeMapper.readValue(json, Object.class);

            return ResponseEntity.ok(Map.of(
                    "status", "imported",
                    "name", node.has("name") ? node.get("name").asText() : "unknown",
                    "parsed_type", parsed.getClass().getSimpleName()
            ));
        } catch (Exception e) {
            log.error("Import failed: {}", e.getMessage());
            return ResponseEntity.badRequest().body(Map.of(
                    "status", "error",
                    "message", e.getMessage()
            ));
        }
    }
}
