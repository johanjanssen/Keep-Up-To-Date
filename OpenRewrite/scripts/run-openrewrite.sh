#!/usr/bin/env bash
# run-openrewrite.sh — Apply OpenRewrite recipes to the demo project.
#
# No plugin configuration in pom.xml is required.  The rewrite-maven-plugin
# is invoked on-the-fly via its Maven coordinates.  Recipe JARs and active
# recipes are passed as -D properties — nothing is baked into the build file.
#
# Usage (run from the OpenRewrite/ directory):
#   bash scripts/run-openrewrite.sh              apply all recipes
#   DRY_RUN=true bash scripts/run-openrewrite.sh preview only, no files changed
#
# ── Recipes ─────────────────────────────────────────────────────────────────
#
#  1. org.openrewrite.java.format.AutoFormat
#       Normalises indentation, spacing and brace placement in every .java file.
#       Bundled with the plugin — no extra artifact needed.
#
#  2. org.openrewrite.staticanalysis.EqualsAvoidsNull
#       variable.equals("literal")  ->  "literal".equals(variable)
#       Eliminates NPE when the variable is null.
#       Artifact: org.openrewrite.recipe:rewrite-static-analysis
#
#  3. org.openrewrite.java.testing.junit5.JUnit4to5Migration
#       Full JUnit 4 -> JUnit 5 (Jupiter) migration:
#         @RunWith(SpringRunner.class)  removed
#         @Before / @After              ->  @BeforeEach / @AfterEach
#         org.junit.Assert.*            ->  org.junit.jupiter.api.Assertions.*
#         @Test(expected=X.class)       ->  assertThrows(X.class, () -> ...)
#         pom.xml: junit:junit + junit-vintage-engine replaced by jupiter
#       Artifact: org.openrewrite.recipe:rewrite-testing-frameworks
#
#  4. org.openrewrite.java.migrate.UpgradeToJava25
#       java.version property: 17 -> 25
#       Multi-line string concatenations with \n  ->  text blocks (""")
#       Deprecated API usages replaced with Java 25 equivalents.
#       Artifact: org.openrewrite.recipe:rewrite-migrate-java
#
#  5. org.openrewrite.java.spring.boot4.UpgradeSpringBoot_4_1
#       spring-boot-starter-parent: 2.7.18  ->  4.1.0
#       javax.*  ->  jakarta.*  (Jakarta EE namespace migration)
#       Spring Security / Actuator / MVC configuration renames
#       Property key renames across spring.* namespaces
#       Chains through Spring Boot 3.0 / 3.1 / 3.2 / 3.3 / 4.0 / 4.1
#       Artifact: org.openrewrite.recipe:rewrite-spring
#
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$PROJECT_DIR")"
MVNW="$ROOT_DIR/mvnw"

# ── Versions ──────────────────────────────────────────────────────────────────
PLUGIN_VERSION="5.42.0"
STATIC_ANALYSIS_VERSION="2.13.0"
TESTING_FRAMEWORKS_VERSION="2.21.0"
MIGRATE_JAVA_VERSION="2.26.0"
REWRITE_SPRING_VERSION="5.21.0"

# ── Recipe library coordinates (comma-separated, NO spaces) ──────────────────
ARTIFACT_COORDS="\
org.openrewrite.recipe:rewrite-static-analysis:${STATIC_ANALYSIS_VERSION},\
org.openrewrite.recipe:rewrite-testing-frameworks:${TESTING_FRAMEWORKS_VERSION},\
org.openrewrite.recipe:rewrite-migrate-java:${MIGRATE_JAVA_VERSION},\
org.openrewrite.recipe:rewrite-spring:${REWRITE_SPRING_VERSION}"

# ── Active recipes (comma-separated, NO spaces) ──────────────────────────────
ACTIVE_RECIPES="\
org.openrewrite.java.format.AutoFormat,\
org.openrewrite.staticanalysis.EqualsAvoidsNull,\
org.openrewrite.java.testing.junit5.JUnit4to5Migration,\
org.openrewrite.java.migrate.UpgradeToJava25,\
org.openrewrite.java.spring.boot4.UpgradeSpringBoot_4_1"

DRY_RUN="${DRY_RUN:-false}"

echo ""
echo "============================================================"
echo "  OpenRewrite Demo - Run Recipes"
echo "============================================================"
echo ""
echo "  Starting state : Spring Boot 2.7.18 / Java 17 / JUnit 4"
echo "  Target state   : Spring Boot 4.1.0  / Java 25 / JUnit 5"
echo ""

if [ ! -f "$MVNW" ]; then
    echo "ERROR: Maven wrapper not found at $MVNW"
    exit 1
fi

if [ "$DRY_RUN" = "true" ]; then
    GOAL="dryRun"
    echo "  DRY-RUN: previewing changes only — no files will be modified."
else
    GOAL="run"
    echo "  LIVE: source files will be rewritten."
fi
echo ""
echo "  Plugin  : org.openrewrite.maven:rewrite-maven-plugin:${PLUGIN_VERSION}"
echo "  Goal    : ${GOAL}"
echo ""
echo "  Recipes :"
echo "    1. org.openrewrite.java.format.AutoFormat"
echo "    2. org.openrewrite.staticanalysis.EqualsAvoidsNull"
echo "    3. org.openrewrite.java.testing.junit5.JUnit4to5Migration"
echo "    4. org.openrewrite.java.migrate.UpgradeToJava25"
echo "    5. org.openrewrite.java.spring.boot4.UpgradeSpringBoot_4_1"
echo ""
echo "------------------------------------------------------------"
echo ""

"$MVNW" -U \
    -f "$PROJECT_DIR/pom.xml" \
    "org.openrewrite.maven:rewrite-maven-plugin:${PLUGIN_VERSION}:${GOAL}" \
    "-Drewrite.recipeArtifactCoordinates=${ARTIFACT_COORDS}" \
    "-Drewrite.activeRecipes=${ACTIVE_RECIPES}"

echo ""
echo "------------------------------------------------------------"
if [ "$DRY_RUN" = "true" ]; then
    echo "OK  Dry run complete."
    echo "    Review the output above, then run without DRY_RUN=true to apply."
else
    echo "OK  Recipes applied."
    echo ""
    echo "  What changed:"
    echo "    pom.xml           spring-boot-starter-parent 2.7.18 -> 4.1.0"
    echo "                      java.version 17 -> 25"
    echo "                      junit:junit + vintage-engine removed"
    echo "    *.java            javax.* imports -> jakarta.*"
    echo "    Person.java       role.equals(...) -> ...equals(role)"
    echo "                      describe() string concat -> text block"
    echo "    GreetingService   name.equals(...) -> ...equals(name)"
    echo "                      getWelcomePage() HTML concat -> text block"
    echo "    *Test.java        @RunWith removed"
    echo "                      @Before -> @BeforeEach, @After -> @AfterEach"
    echo "                      Assert.* -> static Assertions.*"
    echo "                      @Test(expected=) -> assertThrows(...)"
    echo "    All .java files   reformatted (AutoFormat)"
    echo ""
    echo "  Next steps:"
    echo "    1. git diff"
    echo "    2. ../mvnw -f pom.xml test"
    echo "    3. bash scripts/build-image.sh"
fi
echo "------------------------------------------------------------"
echo ""
