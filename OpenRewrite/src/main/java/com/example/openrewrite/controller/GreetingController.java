package com.example.openrewrite.controller;
import com.example.openrewrite.model.Person;
import com.example.openrewrite.service.GreetingService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
/**
 * REST controller — AutoFormat will fix missing spaces and inconsistent
 * brace / indentation style throughout.
 *
 * Spring Boot 3 migration notes applied by UpgradeSpringBoot_3_3:
 *   - @Autowired field injection is kept but flagged; prefer constructor injection.
 *   - Response type may be wrapped in ResponseEntity in the migrated version.
 */
@RestController
@RequestMapping("/api")
public class GreetingController {
// AutoFormat: @Autowired without surrounding whitespace
@Autowired
private GreetingService greetingService;
@GetMapping("/greet")
public String greet(@RequestParam(defaultValue="World") String name){
return greetingService.greet(name);
}
@GetMapping("/welcome")
public String welcomePage(@RequestParam String name){
return greetingService.getWelcomePage(name);
}
@PostMapping("/access")
public boolean checkAccess(@RequestBody Person person,@RequestParam String resource){
return greetingService.canAccess(person,resource);
}
@GetMapping("/reserved")
public boolean isReserved(@RequestParam String name){
return greetingService.isReservedName(name);
}
}
