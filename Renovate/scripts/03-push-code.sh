#!/usr/bin/env bash
# 03-push-code.sh — Commit and push the HelloConference project to Gitea.
#
# Usage:
#   bash Renovate/scripts/03-push-code.sh
#
# What it does:
#   • Copies Renovate/renovate.json to the project root so Renovate can find
#     it at the standard location when scanning the Gitea repository.
#   • Initialises a local Git repository (if not already one).
#   • Stages all project files and creates an initial commit (if needed).
#   • Force-pushes the main branch to Gitea (safe to re-run).
#
# Prerequisites: git, and configured Gitea (run 01 and 02 first)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RENOVATE_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$RENOVATE_DIR")"
TOKEN_FILE="${RENOVATE_DIR}/.env"

GITEA_URL="http://localhost:3000"
ADMIN_USER="gitadmin"
REPO_NAME="hello-conference"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Step 3 — Push code to Gitea"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ── Read token ────────────────────────────────────────────────────────────────
if [ ! -f "${TOKEN_FILE}" ]; then
    echo "❌  Renovate/.env not found. Run: bash Renovate/scripts/02-setup-gitea.sh"
    exit 1
fi
TOKEN=$(grep '^GITEA_TOKEN=' "${TOKEN_FILE}" | cut -d'=' -f2-)
REMOTE_URL="http://${ADMIN_USER}:${TOKEN}@localhost:3000/${ADMIN_USER}/${REPO_NAME}.git"

# ── Copy renovate.json to repository root ─────────────────────────────────────
# Renovate reads its per-repo config from renovate.json at the root of the
# repository being scanned. The canonical source is Renovate/renovate.json;
# this copy is what the Gitea repo exposes to the Renovate bot.
echo "→ Copying Renovate/renovate.json → renovate.json (repo root) …"
cp "${RENOVATE_DIR}/renovate.json" "${PROJECT_DIR}/renovate.json"
echo "   ✅  renovate.json placed at repository root"
echo ""

# ── Move into project root ────────────────────────────────────────────────────
cd "${PROJECT_DIR}"

# ── Initialise Git repo if needed ─────────────────────────────────────────────
if [ ! -d ".git" ]; then
    echo "→ Initialising Git repository …"
    git init
    echo ""
fi

# ── Local git identity (does not touch global ~/.gitconfig) ──────────────────
git config user.email "demo@example.com"
git config user.name  "Conference Demo"
git config init.defaultBranch main

# ── Ensure we are on main ─────────────────────────────────────────────────────
git checkout -b main 2>/dev/null || git checkout main

# ── Add / update the Gitea remote ─────────────────────────────────────────────
echo "→ Configuring remote 'gitea' …"
git remote remove gitea 2>/dev/null || true
git remote add gitea "${REMOTE_URL}"
echo "   ${GITEA_URL}/${ADMIN_USER}/${REPO_NAME}"
echo ""

# ── Stage all files ───────────────────────────────────────────────────────────
echo "→ Staging project files …"
# Ensure mvnw is stored in git with the executable bit (mode 100755).
# Without this, Jenkins checkouts get mode 644 and './mvnw' fails with
# "Permission denied" (exit code 126).
git update-index --chmod=+x mvnw 2>/dev/null || true
git add --all
echo ""

# ── Commit (skip if nothing changed) ─────────────────────────────────────────
if git diff --cached --quiet; then
    echo "   ℹ️   Nothing new to commit — working tree is clean."
else
    echo "→ Creating commit …"
    git commit -m "Initial commit: Spring Boot 4.1 HelloConference demo

- Spring Boot 4.1 + Java 25
- Intentional log4j-core 2.0 (CVE-2021-44228 demo target for Renovate)
- Multi-stage Dockerfiles: jlink, CDS, CRaC, native, distroless
- Jenkinsfile: CI pipeline using eclipse-temurin:25-jdk Docker agent
- renovate.json: update grouping, stability windows, security auto-merge
- Renovate/: Gitea + Jenkins + Renovate local demo infrastructure"
fi
echo ""

# ── Push ──────────────────────────────────────────────────────────────────────
echo "→ Pushing to Gitea …"
git push gitea main --force
echo ""

echo "✅  Code pushed to ${GITEA_URL}/${ADMIN_USER}/${REPO_NAME}"
echo ""
echo "──────────────────────────────────────────────────────────────"
echo "  Repository : ${GITEA_URL}/${ADMIN_USER}/${REPO_NAME}"
echo "  Files      : ${GITEA_URL}/${ADMIN_USER}/${REPO_NAME}/src/branch/main"
echo "  Jenkinsfile: ${GITEA_URL}/${ADMIN_USER}/${REPO_NAME}/src/branch/main/Jenkinsfile"
echo "──────────────────────────────────────────────────────────────"
echo ""
echo "   Next step: bash Renovate/scripts/04-start-jenkins.sh"
echo ""

