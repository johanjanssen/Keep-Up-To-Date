package com.example.mavendependencyplugin.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

/**
 * Exercises the h2 JDBC driver at runtime — deliberately WITHOUT ever importing
 * anything from {@code org.h2.*}.
 * <p>
 * {@link DriverManager} finds h2's driver on its own: every JDBC 4+ driver jar
 * (h2's included) ships a {@code META-INF/services/java.sql.Driver} file, so the
 * driver self-registers via {@link java.util.ServiceLoader} the moment its jar is
 * on the classpath — no {@code Class.forName("org.h2.Driver")}, no direct
 * reference of any kind.
 * <p>
 * That's exactly why {@code mvn dependency:analyze} gets this one wrong: it works
 * by scanning this project's own compiled bytecode for references to each
 * dependency's classes, and there simply isn't one — only {@code java.sql.*}
 * (part of the JDK) appears here. The plugin reports h2 as an "unused declared
 * dependency" even though removing it would make this endpoint fail at runtime
 * with "No suitable driver found for jdbc:h2:...". See pom.xml and
 * scripts/run-dependency-analyze.sh for how the demo handles that.
 */
@RestController
public class DatabaseController {

    private static final String JDBC_URL = "jdbc:h2:mem:demo;DB_CLOSE_DELAY=-1";

    @GetMapping("/db-check")
    public String dbCheck() throws Exception {
        try (Connection connection = DriverManager.getConnection(JDBC_URL, "sa", "");
             Statement statement = connection.createStatement();
             ResultSet resultSet = statement.executeQuery("SELECT 1")) {
            resultSet.next();
            String driverName = connection.getMetaData().getDriverName();
            return "DB check OK (driver: " + driverName + ", result: " + resultSet.getInt(1) + ")";
        }
    }
}
