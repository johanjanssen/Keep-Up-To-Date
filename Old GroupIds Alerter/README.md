# Old GroupIds Alerter Demo

Self-contained demo of the [Old GroupIds Alerter](https://github.com/jonathanlermitage/oga-maven-plugin)
Maven plugin (`oga-maven-plugin`), which checks a project's `pom.xml` against a
community-maintained list of dependencies that have moved to a new Maven
coordinate — usually because the original groupId is no longer maintained.

Based on the same "intentionally old" pattern as the [OpenRewrite](../OpenRewrite/)
and [Vulnerable Application](../Vulnerable%20Application/) demos: a small, real,
buildable Spring Boot app whose `pom.xml` declares dependencies under groupIds
that have since relocated.

---

## Project layout

```
Old GroupIds Alerter/
  pom.xml                          ← 4 dependencies declared under old/moved groupIds
  src/
    main/java/com/example/oldgroupidsalerter/
      OldGroupIdsAlerterDemoApplication.java
      controller/GreetingController.java
    test/java/com/example/oldgroupidsalerter/
      OldGroupIdsAlerterDemoApplicationTests.java
  scripts/
    run-oga.sh                ← run the check (start here)
    generate-html-report.py   ← CI-only: renders findings as the GitHub Pages report
```

---

## The old groupIds

| Declared in pom.xml                          | Should be                                       | Why |
|-----------------------------------------------|--------------------------------------------------|-----|
| `com.graphql-java:graphql-java-tools`          | `com.graphql-java-kickstart:graphql-java-tools`   | The `graphql-java-kickstart` project forked/took over Spring Boot tooling from `graphql-java` in 2019 |
| `javax.xml.bind:jaxb-api`                      | `jakarta.xml.bind:jakarta.xml.bind-api`           | Java EE → Jakarta EE relocation (Oracle handed the Java EE trademark to the Eclipse Foundation) |
| `javax.validation:validation-api`              | `jakarta.validation:jakarta.validation-api`       | Same Jakarta EE relocation |
| `javax.activation:javax.activation-api`        | `jakarta.activation:jakarta.activation-api`       | Same Jakarta EE relocation |

The three `javax.*` dependencies deliberately have **no `<version>`** in
`pom.xml` — `spring-boot-starter-parent:2.7.18`'s BOM manages all three
(`2.3.1`, `2.0.1.Final`, `1.2.0` respectively). That's exactly why they're easy
to miss in a real project: a managed dependency's version doesn't visibly
"look old," so nothing prompts anyone to check whether the groupId itself
still has a maintainer behind it.

---

## Quick start

### Step 1 — Run the check (from `Old GroupIds Alerter/`)

```bash
# Report only — list every finding, build stays green:
bash scripts/run-oga.sh

# Real-world default — build FAILS the moment an old groupId is found:
STRICT=true bash scripts/run-oga.sh
```

Or run the goal directly:

```bash
../mvnw -f pom.xml "biz.lermitage.oga:oga-maven-plugin:1.9.2:check" -DfailOnError=false
```

### Step 2 — Fix pom.xml

For each finding, replace the flagged `<groupId>` (and `<artifactId>`, where
that changed too) with the recommended coordinate, then resolve a compatible
version for it explicitly — versions do **not** carry over from the old
coordinate, managed or not.

### Step 3 — Confirm the gate passes

```bash
STRICT=true bash scripts/run-oga.sh
```

---

## How the plugin works

`biz.lermitage.oga:oga-maven-plugin:check` needs no configuration in `pom.xml`
— it's invoked straight from its Maven coordinates. On each run it downloads
the latest [`og-definitions.json`](https://github.com/jonathanlermitage/oga-maven-plugin/blob/master/uc/og-definitions.json)
(720+ known relocations at the time of writing) from GitHub, walks every
dependency and plugin in the effective POM, and reports any groupId[:artifactId]
match. By default (`failOnError=true`) it fails the build — it's meant to be a
CI gate, not just advice.

---

## GitHub Actions + GitHub Pages report

Pushing changes under `Old GroupIds Alerter/**` to `master` (or running the
workflow manually) triggers
[`.github/workflows/old-groupids-alerter.yml`](../.github/workflows/old-groupids-alerter.yml),
which:

1. Runs the check with `STRICT=true` (the plugin's real default) to show the
   build gate actually failing.
2. Runs it again in report mode (`failOnError=false`) to collect every finding
   in one pass.
3. Renders each finding as a real "before" / "after" `pom.xml` snippet —
   pulled from the actual dependency block in this project's `pom.xml`, not a
   mock-up — and publishes it to GitHub Pages.

Latest report: **https://johanjanssen.github.io/Keep-Up-To-Date/renamed/**
