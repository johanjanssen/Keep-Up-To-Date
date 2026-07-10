# ─────────────────────────────────────────────────────────────────────────────
# OpenRewrite Demo — Dockerfile
#
# Two-stage build so the final image only contains the JRE + application JAR.
#
# Stage 1 (builder): Eclipse Temurin 21 JDK — builds the fat JAR.
# Stage 2 (runtime): Eclipse Temurin 21 JRE (Alpine) — minimal image.
#
# Usage (run from the OpenRewrite/ directory):
#   bash scripts/build-image.sh     # build the image
#   bash scripts/run-image.sh       # run on http://localhost:8080
# ─────────────────────────────────────────────────────────────────────────────
# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /workspace
# Copy Maven wrapper and pom first so dependency layer is cached
COPY .mvn/           .mvn/
COPY mvnw            mvnw
COPY pom.xml         pom.xml
# Download all dependencies (cached unless pom.xml changes)
RUN ./mvnw -B dependency:go-offline -q
# Copy source and build the fat JAR
COPY src/ src/
RUN ./mvnw -B clean package -DskipTests -q
# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM eclipse-temurin:21-jre-alpine
LABEL org.opencontainers.image.title="openrewrite-demo"
LABEL org.opencontainers.image.description="OpenRewrite migration demo — Spring Boot + JUnit 4 before rewrite"
LABEL org.opencontainers.image.base.name="eclipse-temurin:21-jre-alpine"
WORKDIR /app
# Non-root user for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser
COPY --from=builder /workspace/target/openrewrite-demo-*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
