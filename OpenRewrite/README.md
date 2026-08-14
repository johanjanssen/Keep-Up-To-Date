# OpenRewrite Demo

Self-contained demo that shows **OpenRewrite** automatically migrating a
Spring Boot 2 / JUnit 4 / Java 17 project to Spring Boot 4 / JUnit 5 / Java 25.

---

## Project layout

```
OpenRewrite/
  pom.xml                          ← Spring Boot 2.7.18, Java 17, JUnit 4
  Dockerfile                        ← two-stage build, Java 21 runtime
  src/
    main/java/com/example/openrewrite/
      OpenRewriteDemoApplication.java   AutoFormat demo (compact braces)
      controller/GreetingController.java
      service/GreetingService.java       EqualsAvoidsNull + text-block demo
      model/Person.java                  EqualsAvoidsNull + text-block demo
    test/java/com/example/openrewrite/
      GreetingServiceTest.java    JUnit 4: @RunWith, @Before, Assert.*
      PersonTest.java             JUnit 4: @Test(expected=...) pattern
  scripts/
    run-openrewrite.sh       ← run the migration (start here)
    build-image.sh           ← build the Docker image after migration
    run-image.sh             ← run the container
    generate-html-report.py  ← CI-only: renders the diff as the GitHub Pages report
```

---

## Before → after OpenRewrite

| Dimension          | Before                             | After                             |
|---------------------|-------------------------------------|------------------------------------|
| Spring Boot         | `2.7.18`                           | `4.0.x` (latest Spring Boot 4.0 patch) |
| Java source level   | `17`                                | `25`                                |
| Test framework      | JUnit **4** (`junit:junit:4.13.2`) | JUnit **5** (Jupiter)               |
| Code style          | Intentionally inconsistent          | Reformatted (AutoFormat)            |
| Null safety         | `var.equals("literal")` everywhere  | `"literal".equals(var)` everywhere  |

> OpenRewrite's recipe catalog is versioned separately from Spring Boot itself and
> typically lags a release or two behind — at the time of writing the newest
> fixed-version recipe is `UpgradeSpringBoot_4_0`, even though Spring Boot's own
> latest GA release may already be `4.1.x`. See `scripts/run-openrewrite.sh` for
> the exact recipe/version pins in use.

---

## Active recipes

All five recipes are invoked from the command line via `scripts/run-openrewrite.sh` — no plugin configuration in `pom.xml` is needed.  This makes it easy to update recipe versions independently of the build file.

### 1. `org.openrewrite.java.format.AutoFormat`

Reformats all Java source files to the standard IntelliJ/Eclipse style.

```java
// BEFORE
public static void main(String[] args){SpringApplication.run(...);}

// AFTER
public static void main(String[] args) {
    SpringApplication.run(...);
}
```

### 2. `org.openrewrite.staticanalysis.EqualsAvoidsNull`

Moves the literal to the left side of `.equals()` calls to prevent NPE.

```java
// BEFORE — NullPointerException if name is null
if (name.equals("World")) { ... }

// AFTER — null-safe
if ("World".equals(name)) { ... }
```

### 3. `org.openrewrite.java.testing.junit5.JUnit4to5Migration`

Fully migrates JUnit 4 tests to JUnit 5 (Jupiter).

```java
// BEFORE (JUnit 4)
@RunWith(SpringRunner.class)
@SpringBootTest
public class MyTest {
    @Before public void setUp() { ... }
    @After  public void tearDown() { ... }
    @Test   public void testFoo() { Assert.assertEquals(...); }
    @Test(expected = NullPointerException.class)
    public void testThrows() { ... }
}

// AFTER (JUnit 5)
@SpringBootTest
public class MyTest {
    @BeforeEach public void setUp() { ... }
    @AfterEach  public void tearDown() { ... }
    @Test       public void testFoo() { assertEquals(...); }
    @Test
    public void testThrows() { assertThrows(NullPointerException.class, () -> ...); }
}
```

### 4. `org.openrewrite.java.migrate.UpgradeToJava25`

Bumps `java.version` from `17` to `25` and applies modern Java idioms.

```java
// BEFORE — multi-line string concatenation
return "<!DOCTYPE html>\n" +
       "<html>\n" +
       "  <body><p>Hello " + name + "</p></body>\n" +
       "</html>\n";

// AFTER — Java text block
return """
        <!DOCTYPE html>
        <html>
          <body><p>Hello %s</p></body>
        </html>
        """.formatted(name);
```

### 5. `org.openrewrite.java.spring.boot4.UpgradeSpringBoot_4_0`

Upgrades Spring Boot from `2.7.18` all the way to `4.0.x`.  Key changes:

- `spring-boot-starter-parent` version bumped through the full 2→3→4 chain
- `javax.*` imports replaced with `jakarta.*` (Jakarta EE 9+)
- `spring-boot-starter-web` renamed to `spring-boot-starter-webmvc` (Boot 4's modular starters)
- Spring Security, Actuator, and property-key renames applied
- `junit-vintage-engine` and `junit:junit` removed from `pom.xml`
- OpenRewrite chains through Boot 3.0 / 3.1 / 3.2 / 3.3 / 3.4 / 3.5 / 4.0 incrementally

---

## Quick start

### Step 1 — Run the migration (from `OpenRewrite/`)

```bash
# Preview only (no files written):
DRY_RUN=true bash scripts/run-openrewrite.sh

# Apply all five recipes:
bash scripts/run-openrewrite.sh
```

Or run individual Maven goals directly:

```bash
../mvnw -U -f pom.xml \
  "org.openrewrite.maven:rewrite-maven-plugin:6.46.1:dryRun" \
  -Drewrite.recipeArtifactCoordinates=\
org.openrewrite.recipe:rewrite-spring:6.37.0,\
org.openrewrite.recipe:rewrite-testing-frameworks:3.44.0,\
org.openrewrite.recipe:rewrite-migrate-java:3.42.0,\
org.openrewrite.recipe:rewrite-static-analysis:2.41.0 \
  -Drewrite.activeRecipes=\
org.openrewrite.java.format.AutoFormat,\
org.openrewrite.staticanalysis.EqualsAvoidsNull,\
org.openrewrite.java.testing.junit5.JUnit4to5Migration,\
org.openrewrite.java.migrate.UpgradeToJava25,\
org.openrewrite.java.spring.boot4.UpgradeSpringBoot_4_0
```

### Step 2 — Review changes

```bash
git diff
```

### Step 3 — Run the tests

```bash
../mvnw -f pom.xml test
```

Expect **17/18 to pass**. `PersonTest.testIsAdminWithNullRoleThrowsNPE` fails —
on purpose. It asserted the *old buggy* behavior (`role.equals("admin")` throwing
an NPE on a null role); `EqualsAvoidsNull` just fixed that bug by rewriting it to
`"admin".equals(role)`, so the NPE no longer happens. This is the demo's one
deliberate reminder that an automated codemod can fix real bugs while making a
test that encoded the bug fail — the test needs a human to update it to
`assertFalse(nullRolePerson.isAdmin())`.

### Step 4 — Build and run the Docker image

```bash
bash scripts/build-image.sh
bash scripts/run-image.sh
# App available at http://localhost:8080/api/greet?name=World
```

---

## REST endpoints

| Method | URL                          | Description              |
|--------|------------------------------|--------------------------|
| GET    | `/api/greet?name=World`      | Returns greeting string  |
| GET    | `/api/welcome?name=Alice`    | Returns HTML welcome page|
| GET    | `/api/reserved?name=admin`   | Checks reserved names    |
| POST   | `/api/access?resource=secret`| Checks role-based access |

---

## OpenRewrite library versions

| Artifact                      | Version  | Provides                          |
|-------------------------------|----------|-----------------------------------|
| `rewrite-maven-plugin`        | 6.46.1   | Maven integration                 |
| `rewrite-spring`               | 6.37.0   | Spring Boot 2→4 recipes           |
| `rewrite-testing-frameworks`  | 3.44.0   | JUnit 4→5 recipes                 |
| `rewrite-migrate-java`        | 3.42.0   | Java 17→25 migration recipes      |
| `rewrite-static-analysis`     | 2.41.0   | EqualsAvoidsNull etc.             |

> Check [https://docs.openrewrite.org](https://docs.openrewrite.org) for the
> latest recipe versions before running in a real project. These are pinned
> deliberately (not "latest") because the fixed-version upgrade recipes
> (`UpgradeToJava25`, `UpgradeSpringBoot_4_0`, …) only exist from certain
> releases onward — bumping blindly can make Maven fail with
> `Recipe(s) not found`, which is what broke this demo before these versions
> were pinned.

---

## GitHub Actions + GitHub Pages report

Pushing changes under `OpenRewrite/**` to `master` (or running the workflow
manually) triggers [`.github/workflows/openrewrite.yml`](../.github/workflows/openrewrite.yml),
which:

1. Runs the project's existing (pre-migration) tests as a baseline.
2. Applies all five recipes for real, in the ephemeral CI checkout — nothing is
   pushed back to `master`.
3. Runs the tests again against the migrated code.
4. Renders the actual `git diff` plus the before/after test results as a static
   HTML report and publishes it to GitHub Pages.

Latest report: **https://johanjanssen.github.io/Keep-Up-To-Date/OpenRewrite/**
