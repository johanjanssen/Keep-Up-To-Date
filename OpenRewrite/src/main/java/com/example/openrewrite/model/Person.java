package com.example.openrewrite.model;

/**
 * Demo model class — the model layer's contribution to the OpenRewrite demo:
 *
 * <b>EqualsAvoidsNull</b> — {@link #isAdmin()} and {@link #isPrivileged()} call
 * {@code .equals("literal")} on a field that can be {@code null}, which throws a
 * {@link NullPointerException}. OpenRewrite rewrites both to
 * {@code "literal".equals(field)} — including the chained {@code ||} case in
 * {@link #isPrivileged()} — so a null role can no longer blow up either check.
 */
public class Person {

    private String name;
    private int age;
    private String role;

    public Person(String name, int age, String role) {
        this.name = name;
        this.age = age;
        this.role = role;
    }

    public String getName() {
        return name;
    }

    public int getAge() {
        return age;
    }

    public String getRole() {
        return role;
    }

    // ── EqualsAvoidsNull ────────────────────────────────────────────────────
    // BEFORE: role.equals("admin")  →  NullPointerException when role is null
    // AFTER:  "admin".equals(role)  →  null-safe
    public boolean isAdmin() {
        return role.equals("admin");
    }

    // ── EqualsAvoidsNull (chained OR — recipe rewrites both sides) ──────────
    public boolean isPrivileged() {
        return role.equals("admin") || role.equals("superuser");
    }

    public String describe() {
        return """
                Name : %s
                Age  : %d
                Role : %s
                """.formatted(name, age, role);
    }

    @Override
    public String toString() {
        return "Person{name='" + name + "', age=" + age + ", role='" + role + "'}";
    }
}
