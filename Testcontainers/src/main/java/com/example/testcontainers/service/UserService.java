package com.example.testcontainers.service;

import com.example.testcontainers.model.User;
import com.example.testcontainers.repository.UserRepository;

import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class UserService {
    private final UserRepository repo;

    public UserService(UserRepository repo) {
        this.repo = repo;
    }

    public List<User> findAll() {
        return repo.findAll();
    }

    public User findById(Long id) {
        return repo.findById(id)
                .orElseThrow(() -> new RuntimeException("User not found: " + id));
    }

    public User create(User user) {
        return repo.save(user);
    }

    public void delete(Long id) {
        repo.deleteById(id);
    }
}
