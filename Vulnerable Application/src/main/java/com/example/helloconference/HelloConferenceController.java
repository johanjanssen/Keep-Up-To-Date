package com.example.helloconference;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HelloConferenceController {
    @GetMapping("/hello")
    public String hello() {
        return "Hello, YOW!";
    }
}

