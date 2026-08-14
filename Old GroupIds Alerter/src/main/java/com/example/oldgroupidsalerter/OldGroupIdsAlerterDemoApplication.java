package com.example.oldgroupidsalerter;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Old GroupIds Alerter demo application.
 *
 * The app itself does nothing interesting — it exists so pom.xml is a real,
 * buildable Maven project. The point of this demo is the dependency list in
 * pom.xml, not the code. See scripts/run-oga.sh.
 */
@SpringBootApplication
public class OldGroupIdsAlerterDemoApplication {

    public static void main(String[] args) {
        SpringApplication.run(OldGroupIdsAlerterDemoApplication.class, args);
    }
}
