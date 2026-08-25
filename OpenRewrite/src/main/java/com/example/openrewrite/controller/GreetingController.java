package com.example.openrewrite.controller;

import com.example.openrewrite.model.Person;
import com.example.openrewrite.service.GreetingService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

/**
 * REST controller wiring the demo endpoints to {@link GreetingService}.
 */
@RestController
@RequestMapping("/api")
public class GreetingController {

    @Autowired
    private GreetingService greetingService;

    @GetMapping("/greet")
    public String greet(@RequestParam(defaultValue = "World") String name) {
        return greetingService.greet(name);
    }

    @GetMapping("/welcome")
    public String welcomePage(@RequestParam String name) {
        return greetingService.getWelcomePage(name);
    }

    @PostMapping("/access")
    public boolean checkAccess(@RequestBody Person person, @RequestParam String resource) {
        return greetingService.canAccess(person, resource);
    }

    @GetMapping("/reserved")
    public boolean isReserved(@RequestParam String name) {
        return greetingService.isReservedName(name);
    }
}
