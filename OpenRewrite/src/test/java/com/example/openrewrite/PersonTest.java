package com.example.openrewrite;

import com.example.openrewrite.model.Person;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;

/**
 * Pure JUnit 4 unit test (no Spring context) — JUnit4to5Migration recipe
 * rewrites this class to use JUnit 5 annotations and assertion methods.
 *
 * Notable pattern for the demo:
 *   @Test(expected = …)  →  assertThrows(…, () -> { … })  in JUnit 5
 */
public class PersonTest {

    private Person person;
    private Person adminPerson;
    private Person nullRolePerson;

    @Before
    public void setUp() {
        person = new Person("Alice", 30, "user");
        adminPerson = new Person("Bob", 25, "admin");
        // EqualsAvoidsNull demo: nullRolePerson.isAdmin() used in testIsAdminWithNullRoleThrowsNPE
        nullRolePerson = new Person("Charlie", 20, null);
    }

    @Test
    public void testGetters() {
        Assert.assertEquals("Alice", person.getName());
        Assert.assertEquals(30, person.getAge());
        Assert.assertEquals("user", person.getRole());
    }

    @Test
    public void testIsAdmin() {
        Assert.assertFalse(person.isAdmin());
        Assert.assertTrue(adminPerson.isAdmin());
    }

    // ── @Test(expected) → assertThrows (JUnit5) ───────────────────────────
    // BEFORE migration: isAdmin() on a null role throws NPE because it calls
    //   role.equals("admin") — EqualsAvoidsNull fixes this too.
    @Test(expected = NullPointerException.class)
    public void testIsAdminWithNullRoleThrowsNPE() {
        // This test documents the BUG: after EqualsAvoidsNull migration,
        // "admin".equals(null) returns false instead of throwing.
        nullRolePerson.isAdmin();
    }

    @Test
    public void testIsPrivileged() {
        Assert.assertTrue(adminPerson.isPrivileged());
        Assert.assertFalse(person.isPrivileged());
    }

    @Test
    public void testDescribe() {
        String desc = person.describe();
        Assert.assertNotNull(desc);
        Assert.assertTrue(desc.contains("Alice"));
        Assert.assertTrue(desc.contains("30"));
    }

    @Test
    public void testToString() {
        String str = person.toString();
        Assert.assertNotNull(str);
        Assert.assertTrue(str.contains("Alice"));
        Assert.assertTrue(str.contains("user"));
    }
}
