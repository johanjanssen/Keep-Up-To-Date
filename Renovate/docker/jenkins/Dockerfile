FROM jenkins/jenkins:latest-jdk25

USER root

# ── Docker CLI ────────────────────────────────────────────────────────────────
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && . /etc/os-release \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/debian ${VERSION_CODENAME} stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    && groupadd -f -g 999 docker \
    && usermod -aG docker jenkins \
    && rm -rf /var/lib/apt/lists/*

# ── Jenkins plugins ───────────────────────────────────────────────────────────
USER jenkins
COPY --chown=jenkins:jenkins plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli \
        --plugin-file /usr/share/jenkins/ref/plugins.txt \
        --verbose

# ── Runtime configuration ─────────────────────────────────────────────────────
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"
ENV CASC_JENKINS_CONFIG=/var/jenkins_home/casc_configs
