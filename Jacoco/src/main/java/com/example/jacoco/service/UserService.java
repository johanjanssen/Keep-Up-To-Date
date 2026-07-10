package com.example.jacoco.service;

import com.example.jacoco.model.User;

import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.atomic.AtomicLong;

@Service
public class UserService {
    private final Map<Long, User> store = new LinkedHashMap<>();
    private final AtomicLong seq = new AtomicLong(1);

    public List<User> findAll() {
        return new ArrayList<>(store.values());
    }

    public Optional<User> findById(Long id) {
        return Optional.ofNullable(store.get(id));
    }

    public User create(String name, String email) {
        long id = seq.getAndIncrement();
        User u = new User(id, name, email);
        store.put(id, u);
        return u;
    }

    public boolean delete(Long id) {
        return store.remove(id) != null;
    }

    public String diagnostics() {
        return "internal diagnostics: " + store.size() + " users in memory";
    }
}
