package com.example.openrewrite;
import com.example.openrewrite.model.Person;
import com.example.openrewrite.service.GreetingService;
import org.junit.Assert;
import org.junit.Before;
import org.junit.After;
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
 * @SpringBootTest                      @SpringBootTest  (unchanged)
 * @Before                              @BeforeEach
 * @After                               @AfterEach
 * org.junit.Assert.assertEquals(…)     Assertions.assertEquals(…)  (static import)
 * org.junit.Assert.assertTrue(…)       Assertions.assertTrue(…)
 * org.junit.Assert.assertFalse(…)      Assertions.assertFalse(…)
 * org.junit.Assert.assertNotNull(…)    Assertions.assertNotNull(…)
 */
@RunWith(SpringRunner.class)
@SpringBootTest
public class GreetingServiceTest {
    @Autowired
    private GreetingService greetingService;
    private String testName;
    private Person testPerson;
    // ── JUnit4to5Migration: @Before → @BeforeEach ─────────────────────────
    @Before
    public void setUp() {
        testName = "Alice";
        testPerson = new Person("Alice", 30, "user");
    }
    // ── JUnit4to5Migration: @After → @AfterEach ───────────────────────────
    @After
    public void tearDown() {
        testName = null;
        testPerson = null;
    }
    // ── JUnit4to5Migration: Assert.assertEquals → Assertions.assertEquals ─
    @Test
    public void testGreetWorld() {
        String result = greetingService.greet("World");
        Assert.assertNotNull(result);
        Assert.assertEquals("Hello, World!", result);
    }
    @Test
    public void testGreetWithName() {
        String result = greetingService.greet(testName);
        Assert.assertNotNull(result);
        Assert.assertTrue(result.contains(testName));
    }
    @Test
    public void testGreetAdmin() {
        Assert.assertEquals("Hello, Administrator!", greetingService.greet("admin"));
    }
    @Test
    public void testCanAccessAsAdmin() {
        Person admin = new Person("Bob", 25, "admin");
        Assert.assertTrue(greetingService.canAccess(admin, "secret"));
    }
    @Test
    public void testCanAccessPublicResource() {
        Assert.assertTrue(greetingService.canAccess(testPerson, "public"));
    }
    @Test
    public void testCannotAccessPrivateResource() {
        Assert.assertFalse(greetingService.canAccess(testPerson, "secret"));
    }
    @Test
    public void testIsReservedName() {
        Assert.assertTrue(greetingService.isReservedName("admin"));
        Assert.assertFalse(greetingService.isReservedName(testName));
    }
}
