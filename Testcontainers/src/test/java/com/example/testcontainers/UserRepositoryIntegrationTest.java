package com.example.testcontainers;

import com.example.testcontainers.model.User;
import com.example.testcontainers.repository.UserRepository;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Integration test that spins up a real PostgreSQL database using Testcontainers.
 *
 * @ServiceConnection (Spring Boot 3.1+) automatically wires the container's
 * host/port/credentials into the DataSource — no @DynamicPropertySource needed.
 *
 * The static @Container field is shared across all tests in this class:
 * the container starts once and is reused for every @Test method.
 */
@SpringBootTest
@Testcontainers
class UserRepositoryIntegrationTest {

    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> postgres =
            new PostgreSQLContainer<>("postgres:16-alpine");

    @Autowired
    UserRepository userRepository;

    @BeforeEach
    void clean() {
        userRepository.deleteAll();
    }

    @Test
    void savesAndFindsUser() {
        User saved = userRepository.save(new User("Alice", "alice@example.com"));
        assertThat(saved.getId()).isNotNull();
        assertThat(saved.getName()).isEqualTo("Alice");
        User found = userRepository.findById(saved.getId()).orElseThrow();
        assertThat(found.getEmail()).isEqualTo("alice@example.com");
    }

    @Test
    void findsUserByEmail() {
        userRepository.save(new User("Bob", "bob@example.com"));
        assertThat(userRepository.findByEmail("bob@example.com")).isPresent();
        assertThat(userRepository.findByEmail("nobody@example.com")).isEmpty();
    }

    @Test
    void deletesUser() {
        User saved = userRepository.save(new User("Charlie", "charlie@example.com"));
        userRepository.deleteById(saved.getId());
        assertThat(userRepository.findById(saved.getId())).isEmpty();
    }

    @Test
    void findsAllUsers() {
        userRepository.save(new User("Dave", "dave@example.com"));
        userRepository.save(new User("Eve", "eve@example.com"));
        List<User> users = userRepository.findAll();
        assertThat(users).hasSize(2);
    }
}
