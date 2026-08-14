package com.example.openrewrite.model;
/**
 * Demo model class that intentionally contains code patterns that OpenRewrite will fix:
 *
 * <ul>
 *   <li><b>AutoFormat</b>      – missing spaces around operators, compact braces,
 *                                 indentation inconsistencies throughout the class.</li>
 *   <li><b>EqualsAvoidsNull</b> – {@code role.equals("admin")} throws a
 *                                 {@link NullPointerException} when {@code role} is
 *                                 {@code null}.  OpenRewrite rewrites it to
 *                                 {@code "admin".equals(role)}.</li>
 *   <li><b>UpgradeToJava25</b>  – The multi-line string in {@link #describe()} is a
 *                                 perfect candidate for a Java text block. The template
 *                                 is a pure-literal concatenation, interpolated via
 *                                 String.format — UseTextBlocks only rewrites chains of
 *                                 string literals, so any variable interleaved into the
 *                                 concatenation itself would keep it from firing.</li>
 * </ul>
 */
// ── AutoFormat: compact constructor / missing spaces ──────────────────────
public class Person {
private String name;
private int age;
private String role;
public Person(String name,int age,String role){
this.name=name;
this.age=age;
this.role=role;
}
public String getName(){return name;}
public int getAge(){return age;}
public String getRole(){return role;}
// ── EqualsAvoidsNull ──────────────────────────────────────────────────────
// BEFORE: role.equals("admin")  →  NullPointerException when role is null
// AFTER:  "admin".equals(role)  →  null-safe
public boolean isAdmin(){
return role.equals("admin");
}
// ── EqualsAvoidsNull (chained OR) ─────────────────────────────────────────
public boolean isPrivileged(){
return role.equals("admin")||role.equals("superuser");
}
// ── UpgradeToJava25: multi-line string concatenation → text block ─────────
// BEFORE: ugly string concatenation
// AFTER:  clean text block with """
public String describe(){
String template = "Name : %s\n" +
"Age  : %d\n" +
"Role : %s\n";
return String.format(template, name, age, role);
}
// ── AutoFormat: inconsistent spacing around operators ─────────────────────
@Override
public String toString(){
return "Person{name='"+name+"', age="+age+", role='"+role+"'}";
}
}
