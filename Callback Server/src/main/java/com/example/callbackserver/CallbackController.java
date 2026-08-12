package com.example.callbackserver;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Catches all incoming HTTP requests and logs them.
 * Simulates an "attacker's server" receiving callbacks from:
 *   - Log4Shell JNDI lookups (the HTTP portion of the lookup)
 *   - Jackson SSRF (URL class making HTTP connections)
 *   - Any other outbound request triggered by the vulnerable app
 */
@RestController
public class CallbackController {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("HH:mm:ss.SSS");
    private static final AtomicInteger counter = new AtomicInteger(0);
    private static final List<Map<String, Object>> history = new CopyOnWriteArrayList<>();

    // ─────────────────────────────────────────────────────────────
    // Catch-all: logs ANY request to ANY path (except /dashboard)
    // ─────────────────────────────────────────────────────────────
    @RequestMapping("/**")
    public ResponseEntity<String> catchAll(HttpServletRequest request,
                                           @RequestBody(required = false) String body) throws IOException {
        String path = request.getRequestURI();

        // Don't intercept internal paths
        if (path.startsWith("/dashboard") || path.equals("/favicon.ico")
                || path.startsWith("/exploit") || path.startsWith("/exploits")) {
            return ResponseEntity.ok("OK");
        }

        int id = counter.incrementAndGet();
        String timestamp = LocalDateTime.now().format(FMT);
        String method = request.getMethod();
        String client = request.getRemoteAddr() + ":" + request.getRemotePort();
        String queryString = request.getQueryString();
        String fullPath = queryString != null ? path + "?" + queryString : path;

        // Collect headers
        Map<String, String> headers = new LinkedHashMap<>();
        Enumeration<String> headerNames = request.getHeaderNames();
        while (headerNames.hasMoreElements()) {
            String name = headerNames.nextElement();
            headers.put(name, request.getHeader(name));
        }

        // Store in history
        Map<String, Object> entry = new LinkedHashMap<>();
        entry.put("id", id);
        entry.put("timestamp", timestamp);
        entry.put("method", method);
        entry.put("path", fullPath);
        entry.put("client", client);
        entry.put("headers", headers);
        entry.put("body", body);
        history.add(entry);

        // Pretty console output
        String separator = "═".repeat(70);
        System.out.println();
        System.out.println(separator);
        System.out.printf("  🎯 CALLBACK #%d RECEIVED at %s%n", id, timestamp);
        System.out.println(separator);
        System.out.printf("  Method:  %s%n", method);
        System.out.printf("  Path:    %s%n", fullPath);
        System.out.printf("  Client:  %s%n", client);
        System.out.println("  Headers:");
        headers.forEach((k, v) -> System.out.printf("           %s: %s%n", k, v));
        if (body != null && !body.isBlank()) {
            System.out.printf("  Body:    %s%n", body);
        }
        System.out.println(separator);
        System.out.println();

        return ResponseEntity.ok("OK - callback #" + id + " logged\n");
    }

    // ─────────────────────────────────────────────────────────────
    // Dashboard: view all received callbacks as JSON
    // ─────────────────────────────────────────────────────────────
    @GetMapping("/dashboard")
    public ResponseEntity<Map<String, Object>> dashboard() {
        return ResponseEntity.ok(Map.of(
                "total_callbacks", counter.get(),
                "callbacks", history
        ));
    }

    // ─────────────────────────────────────────────────────────────
    // Dashboard: HTML view for presenting at conferences
    // ─────────────────────────────────────────────────────────────
    @GetMapping(value = "/dashboard/live", produces = "text/html")
    public String dashboardHtml() {
        StringBuilder html = new StringBuilder();
        html.append("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>🎯 Callback Server — Live Dashboard</title>
                    <meta http-equiv="refresh" content="2">
                    <style>
                        body { font-family: 'JetBrains Mono', 'Fira Code', monospace; background: #1e1e2e; color: #cdd6f4; padding: 20px; }
                        h1 { color: #f38ba8; }
                        .callback { background: #313244; border-left: 4px solid #f38ba8; padding: 15px; margin: 10px 0; border-radius: 8px; }
                        .callback .id { color: #fab387; font-weight: bold; font-size: 1.2em; }
                        .callback .time { color: #a6adc8; }
                        .callback .method { color: #89b4fa; font-weight: bold; }
                        .callback .path { color: #a6e3a1; }
                        .callback .client { color: #a6adc8; }
                        .empty { color: #6c7086; font-style: italic; padding: 40px; text-align: center; font-size: 1.3em; }
                        .counter { color: #f38ba8; font-size: 2em; margin-bottom: 20px; }
                        table { border-collapse: collapse; width: 100%%; }
                        td, th { padding: 5px 10px; text-align: left; }
                        th { color: #f38ba8; }
                    </style>
                </head>
                <body>
                    <h1>🎯 Callback Server — Live Dashboard</h1>
                    <div class="counter">Callbacks received: %d</div>
                """.formatted(counter.get()));

        if (history.isEmpty()) {
            html.append("<div class='empty'>Waiting for callbacks... Send an exploit to the vulnerable app!</div>");
        } else {
            // Show most recent first
            List<Map<String, Object>> reversed = new ArrayList<>(history);
            Collections.reverse(reversed);
            for (Map<String, Object> entry : reversed) {
                @SuppressWarnings("unchecked")
                Map<String, String> headers = (Map<String, String>) entry.get("headers");
                html.append("<div class='callback'>");
                html.append("<span class='id'>#").append(entry.get("id")).append("</span> ");
                html.append("<span class='time'>").append(entry.get("timestamp")).append("</span><br>");
                html.append("<span class='method'>").append(entry.get("method")).append("</span> ");
                html.append("<span class='path'>").append(entry.get("path")).append("</span><br>");
                html.append("<span class='client'>from ").append(entry.get("client")).append("</span>");
                if (entry.get("body") != null && !entry.get("body").toString().isBlank()) {
                    html.append("<br><b>Body:</b> ").append(entry.get("body"));
                }
                html.append("</div>");
            }
        }

        html.append("</body></html>");
        return html.toString();
    }

    // ─────────────────────────────────────────────────────────────
    // Clear history
    // ─────────────────────────────────────────────────────────────
    @DeleteMapping("/dashboard")
    public ResponseEntity<String> clear() {
        history.clear();
        counter.set(0);
        System.out.println("🗑️  Dashboard cleared.");
        return ResponseEntity.ok("Cleared\n");
    }
}

