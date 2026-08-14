#!/usr/bin/env bash
# Pulls all base images used by the project.
# Plain "image:tag" pulls — always resolves to whatever the tag currently
# points to. `docker pull` is a no-op (just a manifest check, no layer
# download) when the local image already matches, so this stays cheap on a
# machine with a warm local cache; on CI (ubuntu-latest runners start with an
# empty Docker cache every run) it's a full pull regardless of how the FROM
# line is written, so there's nothing to gain from digest-pinning there.
#
#   eclipse-temurin :25-jre/jdk    Temurin 25 (JRE / JDK)
#   azul/zulu-openjdk:25-jdk-crac  Azul Zulu 25 JDK with CRaC patches (crac-azul-distroless-base build)
#   distroless/base-debian12       Debian 12 Bookworm
#   distroless/static-debian12     Debian 12 Bookworm  (static / native-minimal)
#   debian:12-slim                 Debian 12 Bookworm  (native w/ dynamic linking)
#   almalinux/10-base              AlmaLinux 10  Lavender Lion
#   almalinux:10-kitten-minimal    AlmaLinux Kitten 10  Lion Cub  (comparison only)
#   graalvm/native-image-community GraalVM CE 25.0.4 (25i2 interim build; builder, pulled on first docker build)
set -euo pipefail

source "$(dirname "$0")/../images.conf"

for IMG in "${BASE_IMAGES[@]}"; do
    echo "  ↓  Pulling ${IMG} …"
    docker pull "${IMG}"
done
echo "✅  All base images up to date."
