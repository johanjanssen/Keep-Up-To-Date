# Maven Dependency Plugin Demo

Self-contained demo of the [Maven Dependency Plugin](https://maven.apache.org/plugins/maven-dependency-plugin/)'s
`analyze` goal, which compares a project's *declared* `pom.xml` dependencies
against what its compiled bytecode actually *references*, and reports the
mismatches — dead weight worth deleting, but also a well-known category of
false positive: dependencies that are genuinely needed at runtime through
reflection or Java's `ServiceLoader` mechanism, which never show up as a
direct class reference.

Based on the same "intentionally imperfect `pom.xml`" pattern as the
[Old GroupIds Alerter](../Old%20GroupIds%20Alerter/) demo: a small, real,
buildable Spring Boot app whose `pom.xml` declares dependencies chosen to
exercise the plugin, similar in spirit to the [Vulnerable Application Old Java](../Vulnerable%20Application%20Old%20Java/)
demo's "intentionally wrong on purpose" `pom.xml`.

---

## Project layout

```
Maven Dependency Plugin/
  pom.xml                          ← 3 dependencies chosen to trigger findings
  src/
    main/java/com/example/mavendependencyplugin/
      MavenDependencyPluginDemoApplication.java
      controller/GreetingController.java
      controller/DatabaseController.java   ← /db-check — proves h2 is really needed
    test/java/com/example/mavendependencyplugin/
      MavenDependencyPluginDemoApplicationTests.java
  scripts/
    run-dependency-analyze.sh   ← run the check (start here)
    generate-html-report.py     ← CI-only: renders findings as the GitHub Pages report
```

---

## The three findings

`mvn dependency:analyze` reports all three of these as **"Unused declared
dependencies"** — but only two of them actually are:

| Declared in pom.xml | What it really is | Verdict |
|---|---|---|
| `org.apache.commons:commons-lang3` | Never imported anywhere in `src/` | ✅ Genuinely unused — delete it |
| `com.google.guava:guava` | Never imported anywhere in `src/` | ✅ Genuinely unused — delete it |
| `com.h2database:h2` | Used at runtime by `DatabaseController` (`/db-check`) — but only through `java.sql.DriverManager` + the JDBC 4 `ServiceLoader` mechanism (h2's own jar ships `META-INF/services/java.sql.Driver`), never a direct `org.h2.*` import | ❌ **False positive** — keep it |

`dependency:analyze` works by scanning this project's own **compiled
bytecode** for class references into each dependency's jar. It has no way to
see a dependency that's only ever reached through reflection or a
`ServiceLoader` lookup — which is exactly how nearly every JDBC driver,
logging bridge, and many annotation processors are loaded. Treat every
finding as a starting point for a human decision, not an automatic deletion.

The real fix for the false positive isn't to delete the dependency — it's to
tell the plugin explicitly that it's used, via `<usedDependencies>`:

```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-dependency-plugin</artifactId>
    <configuration>
        <usedDependencies>
            <usedDependency>com.h2database:h2</usedDependency>
        </usedDependencies>
    </configuration>
</plugin>
```

(`pom.xml` in this demo already uses the same mechanism —
`<ignoredUsedUndeclaredDependencies>` — to silence separate, unrelated noise
from the Spring Boot starter POMs; see the comment on that `<plugin>` block.)

---

## Quick start

### Step 1 — Run the check (from `Maven Dependency Plugin/`)

```bash
# Report only — list every finding, build stays green:
bash scripts/run-dependency-analyze.sh

# Opt-in CI gate — build FAILS if any finding remains (NOT the plugin's own default):
STRICT=true bash scripts/run-dependency-analyze.sh
```

Or run the goal directly:

```bash
../mvnw -f pom.xml test-compile "org.apache.maven.plugins:maven-dependency-plugin:3.11.0:analyze" -DfailOnWarning=false
```

### Step 2 — See the driver actually get used

```bash
../mvnw -f pom.xml spring-boot:run
# in another shell:
curl http://localhost:8080/db-check
# → DB check OK (driver: H2 JDBC Driver, result: 1)
```

Nothing in `src/` imports `org.h2.*` — yet the endpoint works. That's the
false positive in action.

### Step 3 — Fix `pom.xml`

- Delete the `commons-lang3` and `guava` `<dependency>` blocks.
- Keep the `h2` `<dependency>` and add the `<usedDependencies>` suppression
  shown above.

### Step 4 — Confirm the gate passes

```bash
STRICT=true bash scripts/run-dependency-analyze.sh
```

---

## How the plugin works

`org.apache.maven.plugins:maven-dependency-plugin:analyze` needs no
configuration in `pom.xml` to run — it's invoked straight from its Maven
coordinates against whatever is already compiled in `target/classes` and
`target/test-classes`. For each declared dependency it checks whether any
class in that dependency's jar is referenced by this project's own compiled
bytecode, and reports two kinds of mismatch: **unused declared** (declared
but never referenced — the finding this demo focuses on) and **used
undeclared** (referenced, but only pulled in transitively, not declared
directly — not part of this demo's narrative, so the Spring Boot starter
POMs that would otherwise show up here are suppressed via
`<ignoredUsedUndeclaredDependencies>`).

Unlike the [Old GroupIds Alerter](../Old%20GroupIds%20Alerter/) plugin's
`check` goal, `analyze`'s `failOnWarning` parameter **defaults to `false`** —
it's advisory out of the box. `STRICT=true` above opts into the CI gate real
teams typically add on top; it does not reproduce a plugin default.

---

## GitHub Actions + GitHub Pages report

Pushing changes under `Maven Dependency Plugin/**` to `master` (or running the
workflow manually) triggers
[`.github/workflows/maven-dependency-plugin.yml`](../.github/workflows/maven-dependency-plugin.yml),
which:

1. Runs the check with `STRICT=true` to show the opt-in CI gate actually
   failing.
2. Runs it again in report mode (`failOnWarning=false`) to collect every
   finding in one pass.
3. Renders each finding as a real "before" / "after" `pom.xml` snippet —
   pulled from the actual dependency block in this project's `pom.xml`, not a
   mock-up — with a different "after" for the two genuinely unused
   dependencies (deleted) versus the h2 false positive (kept, with
   `<usedDependencies>` added) — and publishes it to GitHub Pages.

Latest report: **https://johanjanssen.github.io/Keep-Up-To-Date/dependency/**
