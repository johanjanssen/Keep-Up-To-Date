#!/usr/bin/env bash
# Pulls all base images used by the project.
# image:tag@sha256:digest → Docker uses the local cache when the digest is already
# present; no network traffic occurs.  Update digests here to upgrade intentionally.
#
#   eclipse-temurin :25-jre/jdk    Temurin 25.0.3+9 / Ubuntu 26.04
#   azul/zulu-openjdk:25-jdk-crac  Azul Zulu 25 JDK with CRaC patches (crac-azul-distroless-base build)
#   distroless/base-debian13       Debian 13 Trixie
#   distroless/static-debian13     Debian 13 Trixie  (static / native-minimal)
#   debian:13-slim                 Debian 13 Trixie  (native w/ dynamic linking)
#   almalinux/10-base              AlmaLinux 10.2  Lavender Lion
#   almalinux:10-kitten-minimal    AlmaLinux Kitten 10  Lion Cub  (comparison only)
#   graalvm/native-image-community GraalVM CE 25  (builder; pulled on first docker build)
set -euo pipefail

source "$(dirname "$0")/../images.conf"

# Pinned digests for reproducible builds – keyed by the base image name from images.conf.
declare -A DIGESTS=(
    ["eclipse-temurin:25-jre"]="sha256:7ea65de6187ad8fbcc0ad155950c38664a7371148bb3ccf1ec1e1b286b44ad08"
    ["eclipse-temurin:25-jdk"]="sha256:dfc0093e3dbf43dae57827111c6e374f5b44fac19a9451584b2b336b81474d64"
    ["gcr.io/distroless/base-debian13"]="sha256:f4a335ca209e1d2ee873102c17c389ad0142e3d5b21aee2817e9cc9c01d87d20"
    ["gcr.io/distroless/static-debian13"]="sha256:9197324ba51d9cd071af8505989365c006adf9d6d2067eada25aef00abbb5278"
    ["debian:13-slim"]="sha256:3a39a0592364683e6bab97937b72cad5a8fa6dcbbee90edb3bb48c7f8e94f258"
    ["almalinux/10-base"]="sha256:44c3e178effb6173e8d29e08e3c76b6799f91defb93e4590125912bdbfd686b9"
    ["almalinux:10-kitten-minimal"]="sha256:515a829404b2b5d25d0da6f6c8359bcc83d54974c9ce829a8854ac3f792a20ed"
    ["ghcr.io/graalvm/native-image-community:25"]="sha256:0d936f32bb8acb5bc60c41b33e05f064d7a6aaf36b726538296c54949bd4a3c0"
)

for IMG in "${BASE_IMAGES[@]}"; do
    DIGEST="${DIGESTS[$IMG]:-}"
    PULL_REF="${IMG}"
    [[ -n "${DIGEST}" ]] && PULL_REF="${IMG}@${DIGEST}"

    if docker image inspect "${PULL_REF}" >/dev/null 2>&1; then
        echo "  ✓  ${PULL_REF}  (already cached – skipping pull)"
    else
        echo "  ↓  Pulling ${PULL_REF} …"
        docker pull "${PULL_REF}"
    fi

    # A digest pull only creates the "image@sha256:..." reference — it does NOT
    # create the plain "image:tag" reference that images.conf / the scan scripts
    # look up. Tag it explicitly so downstream tools resolve the *pinned* digest
    # instead of silently re-pulling (and scanning) whatever "tag" points to now.
    if [[ -n "${DIGEST}" ]]; then
        docker tag "${PULL_REF}" "${IMG}"
    fi
done
echo "✅  All base images up to date."

