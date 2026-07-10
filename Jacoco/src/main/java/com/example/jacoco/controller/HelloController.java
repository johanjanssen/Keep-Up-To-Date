package com.example.jacoco.controller;

import com.example.jacoco.model.User;
import com.example.jacoco.service.UserService;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
public class HelloController {
    private final UserService userService;

    public HelloController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping("/hello")
    public Map<String, String> hello(@RequestParam(defaultValue = "World") String name) {
        return Map.of("message", "Hello, " + name + "!");
    }

    @GetMapping("/users")
    public List<User> users() {
        return userService.findAll();
    }

    @GetMapping("/users/{id}")
    public ResponseEntity<User> user(@PathVariable Long id) {
        return userService.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/users")
    public User create(@RequestBody Map<String, String> body) {
        return userService.create(body.get("name"), body.get("email"));
    }

    @GetMapping("/admin/diagnostics")
    public Map<String, String> diagnostics() {
        return Map.of("result", userService.diagnostics());
    }
}
