package com.example.openrewrite.service;
import com.example.openrewrite.model.Person;
import org.springframework.stereotype.Service;
import java.util.List;
import java.util.ArrayList;
/**
 * Business-logic service — intentional issues for each OpenRewrite recipe:
 *
 * AutoFormat        – missing spaces, compact bodies, inconsistent braces.
 * EqualsAvoidsNull  – greet() and canAccess() call .equals() on a variable
 *                     that may be null; recipe rewrites to literal.equals(var).
 * UpgradeToJava25   – getWelcomePage() builds HTML via string concatenation
 *                     with embedded newlines; recipe converts to a text block.
 *                     (The template is built as a pure-literal concatenation
 *                     and interpolated with String.format — UseTextBlocks only
 *                     rewrites concatenations of string literals; if a variable
 *                     like `name` is interleaved into the chain it leaves the
 *                     whole expression alone, since text blocks can't embed
 *                     expressions the way the original concatenation could.)
 */
@Service
public class GreetingService {
private static final List<String> RESERVED_NAMES=new ArrayList<>();
static{
RESERVED_NAMES.add("admin");
RESERVED_NAMES.add("root");
RESERVED_NAMES.add("system");
}
// ── EqualsAvoidsNull: name.equals("World") throws NPE when name is null ───
public String greet(String name){
if(name.equals("World")){return "Hello, World!";}
if(name.equals("admin")){return "Hello, Administrator!";}
return "Hello, "+name+"!";
}
// ── UpgradeToJava25: multi-line concatenation → text block ────────────────
public String getWelcomePage(String name){
String template="<!DOCTYPE html>\n"+
"<html>\n"+
"  <head><title>Welcome</title></head>\n"+
"  <body>\n"+
"    <h1>Welcome, %s!</h1>\n"+
"    <p>OpenRewrite demo application.</p>\n"+
"  </body>\n"+
"</html>\n";
return String.format(template,name);
}
// ── EqualsAvoidsNull: person.getRole().equals("admin") ────────────────────
public boolean canAccess(Person person,String resource){
if(person.getRole().equals("admin")){return true;}
if(resource.equals("public")){return true;}
return false;
}
public boolean isReservedName(String name){
return RESERVED_NAMES.contains(name);
}
}
