package com.example.oldgroupidsalerter.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * A single trivial endpoint, just to give the app something to run.
 * The old-groupid dependencies in pom.xml are declared but never imported —
 * see the comment there for why.
 */
@RestController
public class GreetingController {

    @GetMapping("/api/greet")
    public String greet(@RequestParam(defaultValue = "World") String name) {
        return "Hello, " + name + "!";
    }
}
