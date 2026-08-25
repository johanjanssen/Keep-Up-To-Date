package com.example.mavendependencyplugin.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class GreetingController {

    @GetMapping("/")
    public String greet() {
        return "Maven Dependency Plugin demo — see /db-check for the JDBC driver false positive";
    }
}
