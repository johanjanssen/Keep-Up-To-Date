package com.example.openrewrite.repository;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

/**
 * Demo repository — the security example, kept deliberately separate from the
 * Spring beans above so the vulnerability (and its fix) stand on their own.
 *
 * <b>FixSqlInjectionConcat</b> (rewrite-java-security) — {@link #findByName} builds a
 * query by splicing an untrusted parameter straight into the SQL string: a classic
 * SQL-injection hole (a {@code name} of {@code ' OR '1'='1} returns every row, not just
 * one user). The recipe rewrites the {@link Statement} to a {@link java.sql.PreparedStatement}
 * with a bound {@code ?} parameter, which the JDBC driver escapes for you.
 */
public class UserRepository {

    public ResultSet findByName(Connection conn, String name) throws SQLException {
        Statement stmt = conn.createStatement();
        return stmt.executeQuery("SELECT * FROM users WHERE name = '" + name + "'");
    }
}
