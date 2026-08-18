#!/usr/bin/env bash
# Pulls all base images used by the project.
# Plain "image:tag" pulls — always resolves to whatever the tag currently
# points to. `docker pull` is a no-op (just a manifest check, no layer
# download) when the local image already matches, so this stays cheap on a
# machine with a warm local cache; on CI (ubuntu-latest runners start with an
# empty Docker cache every run) it's a full pull regardless of how the FROM
# line is written, so there's nothing to gain from digest-pinning there.
#
#   eclipse-temurin :25-jre/jdk     Temurin 25 (JRE / JDK)
#   azul/zulu-openjdk:25-jdk-crac   Azul Zulu 25 JDK with CRaC patches (crac-azul-distroless-base build)
#   distroless/base-debian13        Debian 13 Trixie
#   distroless/static-debian13      Debian 13 Trixie  (static / native-minimal)
#   debian:13-slim                  Debian 13 Trixie  (native w/ dynamic linking)
#   almalinux/10-base               AlmaLinux 10  Lavender Lion
#   almalinux/10-micro              AlmaLinux 10  Lavender Lion  (stripped-down, no package manager)
#   almalinux:10-kitten-minimal     AlmaLinux Kitten 10  Lion Cub  (comparison only)
#   graalvm/native-image-community  GraalVM CE 25.0.4 (25i2 interim build; builder, pulled on first docker build)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../images.conf"

for IMG in "${BASE_IMAGES[@]}"; do
    # "scratch-probe:local" stands in for "scratch" — a reserved pseudo-image
    # built into the Docker daemon (empty filesystem, no registry manifest),
    # so `docker pull scratch` always fails with "reserved name". Building
    # the one-line Dockerfile.scratch-probe is the only way to get a real,
    # inspectable local image for it, so build it instead of pulling.
    if [[ "${IMG}" == "scratch-probe:local" ]]; then
        echo "  ⚙  Building ${IMG} (FROM scratch; not fetchable from a registry) …"
        docker build -t "${IMG}" -f "${SCRIPT_DIR}/Dockerfile.scratch-probe" "${SCRIPT_DIR}"
        continue
    fi
    echo "  ↓  Pulling ${IMG} …"
    docker pull "${IMG}"
done
echo "✅  All base images up to date."
