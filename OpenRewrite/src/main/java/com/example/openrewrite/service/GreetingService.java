package com.example.openrewrite.service;

import com.example.openrewrite.model.Person;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

/**
 * Business-logic service — the demo's one <b>UpgradeToJava25</b> example.
 *
 * {@link #getWelcomePage(String)} builds HTML via string concatenation with
 * embedded newlines; the recipe converts it to a text block. (The template is
 * a pure-literal concatenation interpolated via String.format — UseTextBlocks
 * only rewrites concatenations of string literals; a variable interleaved into
 * the chain itself would keep it from firing.)
 */
@Service
public class GreetingService {

    private static final List<String> RESERVED_NAMES = new ArrayList<>();

    static {
        RESERVED_NAMES.add("admin");
        RESERVED_NAMES.add("root");
        RESERVED_NAMES.add("system");
    }

    public String greet(String name) {
        if ("World".equals(name)) {
            return "Hello, World!";
        }
        if ("admin".equals(name)) {
            return "Hello, Administrator!";
        }
        return "Hello, " + name + "!";
    }

    // ── UpgradeToJava25: multi-line concatenation → text block ────────────
    public String getWelcomePage(String name) {
        String template = "<!DOCTYPE html>\n" +
                "<html>\n" +
                "  <head><title>Welcome</title></head>\n" +
                "  <body>\n" +
                "    <h1>Welcome, %s!</h1>\n" +
                "    <p>OpenRewrite demo application.</p>\n" +
                "  </body>\n" +
                "</html>\n";
        return String.format(template, name);
    }

    public boolean canAccess(Person person, String resource) {
        if ("admin".equals(person.getRole())) {
            return true;
        }
        return "public".equals(resource);
    }

    public boolean isReservedName(String name) {
        return RESERVED_NAMES.contains(name);
    }
}
