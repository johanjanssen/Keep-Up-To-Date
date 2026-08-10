package com.example.callbackserver;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Serves static files from /app/static/ — including the compiled exploit class.
 * The malicious ExploitPayload.class is served at /exploit/ExploitPayload.class
 */
@Configuration
public class StaticResourceConfig implements WebMvcConfigurer {

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        registry.addResourceHandler("/exploit/**")
                .addResourceLocations("file:/app/static/exploit/");
    }
}

