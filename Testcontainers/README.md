# Testcontainers Demo

Spring Boot 4.1 / Java 25 integration tests using a **real** PostgreSQL container
— no mocks, no in-memory fakes.

---

## What this demo shows

| What | How |
|---|---|
| PostgreSQL CRUD | `UserRepositoryIntegrationTest` — saves, finds, deletes via JPA |
| `@ServiceConnection` | Spring Boot 3.1+ auto-wires container host/port/credentials into `DataSource` — no `@DynamicPropertySource` boilerplate |

---

## Quick start

```bash
# Requires: Docker running locally
bash scripts/run-tests.sh

# Or directly with Maven:
../mvnw -f pom.xml test
```

Testcontainers automatically pulls `postgres:16-alpine` on first run (~10 s).
Subsequent runs use the Docker layer cache.

---

## REST endpoints (run the app)

```bash
# Start the app (needs a real Postgres — use docker-compose or Testcontainers DevMode)
../mvnw -f pom.xml spring-boot:run

# User CRUD
curl http://localhost:8080/users
curl -X POST http://localhost:8080/users -H "Content-Type: application/json" \
     -d '{"name":"Alice","email":"alice@example.com"}'
curl http://localhost:8080/users/1
curl -X DELETE http://localhost:8080/users/1
```

---

## How `@ServiceConnection` works

```java
@Container
@ServiceConnection                     // ← Spring Boot reads host/port/credentials
static PostgreSQLContainer<?> postgres  //   and auto-configures the DataSource
    = new PostgreSQLContainer<>("postgres:16-alpine");
```

Before Spring Boot 3.1, you needed:
```java
@DynamicPropertySource
static void props(DynamicPropertyRegistry r) {
    r.add("spring.datasource.url",      postgres::getJdbcUrl);
    r.add("spring.datasource.username", postgres::getUsername);
    r.add("spring.datasource.password", postgres::getPassword);
}
```

`@ServiceConnection` eliminates this boilerplate entirely.

---

## Project structure

```
src/
  main/java/com/example/testcontainers/
    controller/UserController.java     GET/POST/DELETE /users
    model/User.java                    JPA entity
    repository/UserRepository.java     JpaRepository<User, Long>
    service/UserService.java           CRUD logic
  test/java/com/example/testcontainers/
    UserRepositoryIntegrationTest.java  PostgreSQL container tests
```

---

## Key dependencies

| Dependency | Purpose |
|---|---|
| `spring-boot-starter-data-jpa` | JPA / Hibernate |
| `postgresql` (runtime) | JDBC driver |
| `spring-boot-testcontainers` | `@ServiceConnection` support |
| `testcontainers:postgresql` | PostgreSQL Testcontainer |

