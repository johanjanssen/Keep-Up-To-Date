package com.example.openrewrite;

import com.example.openrewrite.model.Person;
import com.example.openrewrite.service.GreetingService;
import org.junit.After;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.junit4.SpringRunner;

/**
 * JUnit 4 integration test — JUnit4to5Migration recipe rewrites this to JUnit 5:
 *
 * BEFORE (JUnit 4)                     AFTER (JUnit 5 — Jupiter)
 * ─────────────────────────────────    ─────────────────────────────────────
 * @RunWith(SpringRunner.class)          removed (no longer needed)
 * @Before / @After                      @BeforeEach / @AfterEach
 * org.junit.Assert.*                    Assertions.* (static import)
 */
@RunWith(SpringRunner.class)
@SpringBootTest
public class GreetingServiceTest {

    @Autowired
    private GreetingService greetingService;
    private Person testPerson;

    @Before
    public void setUp() {
        testPerson = new Person("Alice", 30, "user");
    }

    @After
    public void tearDown() {
        testPerson = null;
    }

    @Test
    public void testGreetVariants() {
        Assert.assertEquals("Hello, World!", greetingService.greet("World"));
        Assert.assertEquals("Hello, Administrator!", greetingService.greet("admin"));
        Assert.assertTrue(greetingService.greet("Alice").contains("Alice"));
    }

    @Test
    public void testAccessControl() {
        Person admin = new Person("Bob", 25, "admin");
        Assert.assertTrue(greetingService.canAccess(admin, "secret"));
        Assert.assertTrue(greetingService.canAccess(testPerson, "public"));
        Assert.assertFalse(greetingService.canAccess(testPerson, "secret"));
    }

    @Test
    public void testIsReservedName() {
        Assert.assertTrue(greetingService.isReservedName("admin"));
        Assert.assertFalse(greetingService.isReservedName("Alice"));
    }
}
