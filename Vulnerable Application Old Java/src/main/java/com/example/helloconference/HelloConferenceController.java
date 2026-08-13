package com.example.helloconference;

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
 * invisible in the code — they come from the dependencies. Every stage logs
 * clearly so a conference audience can follow request -> processing ->
 * outcome from the raw application logs, without needing to read the exploit
 * code to know what happened.
 */
@RestController
public class HelloConferenceController {

    // ⚠️ Using Log4j 2.14.1 directly — vulnerable to Log4Shell (CVE-2021-44228)
    private static final Logger log = LogManager.getLogger(HelloConferenceController.class);

    // ⚠️ Jackson 2.13.4.1 with default typing — vulnerable to deserialization RCE
    // (CVE-2022-42003 / CVE-2022-42004 class of issues; enableDefaultTyping() is
    // deprecated for exactly this reason). This is a real internal-service
    // pattern: two Spring Boot services that share the same ObjectMapper config
    // exchange JSON that's already in Jackson's polymorphic "[class, value]"
    // wire format — neither side hand-writes it, Jackson adds/reads it
    // transparently on both ends. That's what makes it dangerous: the wrapper
    // format looks like normal internal traffic, not something suspicious.
    @SuppressWarnings("deprecation")
    private static final ObjectMapper unsafeMapper = new ObjectMapper() {{
        enableDefaultTyping();
    }};

    @GetMapping("/hello")
    public String hello() {
        return "Hello, YOW!";
    }

    // ─────────────────────────────────────────────────────────────────
    // DEMO 1 — Log4Shell  (CVE-2021-44228)
    // ─────────────────────────────────────────────────────────────────
    // A perfectly normal product search endpoint. The developer just logs
    // user input — standard practice, and arguably good practice for
    // observability. The vulnerability is entirely in log4j-core 2.14.1,
    // which interprets JNDI lookup expressions found anywhere in a logged
    // message, not something wrong with this handler's logic.
    // ─────────────────────────────────────────────────────────────────
    @GetMapping("/api/products/search")
    public ResponseEntity<Map<String, Object>> searchProducts(@RequestParam String q) {
        log.info("[search] Received request");

        // This is the vulnerable line — the ONLY one that logs the raw query
        // value. It looks unremarkable: log the search term so we can see
        // what people are searching for. Log4j 2.14.1 resolves ${...}
        // lookups inside the *rendered* message — string concatenation and
        // "{}" parameter substitution are both affected, so this single line
        // is enough; the other log lines around it deliberately avoid
        // re-logging the raw value; a real Log4Shell payload would otherwise
        // fire once per log line that includes it, which just muddies a demo.
        log.info("Product search query: " + q);

        List<Map<String, String>> catalog = List.of(
                Map.of("id", "1", "name", "Conference T-Shirt", "price", "25.00"),
                Map.of("id", "2", "name", "Speaker Badge", "price", "5.00"),
                Map.of("id", "3", "name", "Workshop Notebook", "price", "12.50")
        );

        List<Map<String, String>> filtered = catalog.stream()
                .filter(p -> p.get("name").toLowerCase().contains(q.toLowerCase()))
                .collect(Collectors.toList());

        log.info("[search] Returning {} match(es)", filtered.size());

        return ResponseEntity.ok(Map.of(
                "query", q,
                "count", filtered.size(),
                "results", filtered
        ));
    }

    // ─────────────────────────────────────────────────────────────────
    // DEMO 2 — Jackson Deserialization RCE  (default-typing gadget chains)
    // ─────────────────────────────────────────────────────────────────
    // An internal "profile sync" endpoint: the request body is whatever the
    // shared ObjectMapper (enableDefaultTyping) produces, e.g.
    //   ["java.util.LinkedHashMap", {"name":"Alice","email":"alice@conf.io"}]
    // Nobody hand-writes that — it's what Jackson emits automatically when
    // any Java service on this stack serializes a profile object. Default
    // typing applies the SAME "[class, value]" wrapping recursively to every
    // Object-typed value nested inside, which is exactly the gadget: an
    // attacker who can reach this endpoint doesn't need to replace the whole
    // body with something suspicious, just swap ONE nested value's class.
    // ─────────────────────────────────────────────────────────────────
    @PostMapping("/api/users/import")
    public ResponseEntity<Map<String, Object>> importUser(@RequestBody String json) {
        log.info("[import] Received user-import request ({} bytes)", json.length());
        try {
            Object parsed = unsafeMapper.readValue(json, Object.class);
            log.info("[import] Jackson resolved the request body to runtime type: {}", parsed.getClass().getName());

            if (parsed instanceof Map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> profile = (Map<String, Object>) parsed;
                // Realistic defensive logging: report the *actual runtime class*
                // of every field value. In normal use these are always
                // String/Number/Boolean/List/Map — anything else means Jackson
                // instantiated a class the client named, not one this code chose.
                profile.forEach((key, value) -> {
                    Class<?> type = value == null ? null : value.getClass();
                    boolean expected = value == null || value instanceof String
                            || value instanceof Number || value instanceof Boolean
                            || value instanceof Map || value instanceof List;
                    if (!expected) {
                        log.warn("[import] field \"{}\" deserialized as {} — attacker-controlled type, not an expected profile field type!",
                                key, type.getName());
                    } else {
                        log.info("[import] field \"{}\" = {} ({})", key, value, type == null ? "null" : type.getSimpleName());
                    }
                });
                return ResponseEntity.ok(Map.of(
                        "status", "imported",
                        "name", String.valueOf(profile.getOrDefault("name", "unknown"))
                ));
            }

            // The request body deserialized to something that isn't even a
            // profile map — e.g. the attacker replaced the *entire* wrapper's
            // class, not just a nested field. Still logged, still visible.
            log.warn("[import] Request body did not resolve to a profile map — resolved type was {}", parsed.getClass().getName());
            return ResponseEntity.ok(Map.of(
                    "status", "imported",
                    "resolved_type", parsed.getClass().getName()
            ));
        } catch (Exception e) {
            log.error("[import] Failed to import profile: {}", e.getMessage());
            return ResponseEntity.badRequest().body(Map.of(
                    "status", "error",
                    "message", String.valueOf(e.getMessage())
            ));
        }
    }
}
