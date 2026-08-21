#!/usr/bin/env bash
# Shared helpers for the "Vulnerable App — Full Demo" workflow's step-summary scripts.
#
# Why this exists: a `run:` step's script source is always echoed into the raw GitHub
# Actions log before it executes. When every line here was
# `echo "some sentence" >> $GITHUB_STEP_SUMMARY`, that echoed source WAS the entire
# visible log — the real commands (curl / docker exec / docker logs) and their results
# only ever reached the summary file, invisible until the job finished and someone
# opened the rendered summary page. The raw log then read as a wall of
# "echo ... echo ... echo ..." with no commands or results in it at all.
#
# run_live / run_json / run_pipe fix that: each prints "$ <command>" and tees the real
# output to BOTH the live log (so you can watch it happen while the job runs) AND the
# summary (so the finished page reads as a clean "command → result" transcript).
#
# Sourced (not executed) from each step: `source scripts/demo-log.sh`.
#
# Why $S is NOT $GITHUB_STEP_SUMMARY: that env var points to a file that's unique to
# EACH STEP — GitHub creates a fresh one per step and only concatenates them for
# display in the Actions UI afterward. Each demo job here spans several steps
# ("Fire the exploit", "Watching it happen", "Forensics", ...), so if $S were
# $GITHUB_STEP_SUMMARY directly, every step's writes would land in a different file
# that the next step can't see, and the final "Save summary for GitHub Pages" step
# — which just does `cp "$S" NN-slug.md` — would only ever capture its own empty
# contribution, not the transcript built up over the whole job. (This is exactly
# what happened before this fix: the published /vulnerable page rendered empty
# sections.) A plain file in the job's workspace persists across steps of the same
# job like any other file docker/curl/etc. touch, so that's what $S points to
# instead; the "Save summary" step separately copies it into that step's own
# $GITHUB_STEP_SUMMARY too, so the Actions UI's own Summary tab still shows the
# full transcript, not just this file's slice of it.

S="${DEMO_LOG_FILE:-demo-log.md}"

# run_live <label> <command...>
# Prints "$ <label>" then runs <command...> as normal argv (quote arguments the usual
# way — no extra shell-escaping needed), showing combined stdout+stderr both in the
# live Actions log and inside a ```console fence in the summary.
run_live() {
    local label="$1"; shift
    printf '```console\n$ %s\n' "$label" >> "$S"
    echo "+ ${label}"
    local out
    out=$("$@" 2>&1) || true
    [ -n "$out" ] && echo "$out"
    printf '%s\n```\n\n' "$out" >> "$S"
}

# run_pipe <label> <shell-command-string>
# Same as run_live, but for pipelines (e.g. "docker logs x | grep ...") that need a
# real shell to parse them — passed as a single string and run via bash -c.
run_pipe() {
    local label="$1" cmd="$2"
    printf '```console\n$ %s\n' "$label" >> "$S"
    echo "+ ${label}"
    local out
    out=$(bash -o pipefail -c "$cmd" 2>&1) || true
    [ -n "$out" ] && echo "$out"
    printf '%s\n```\n\n' "$out" >> "$S"
}

# run_json <label> <command...>
# Same as run_live, but the response is pretty-printed as its own ```json fence
# (falls back to raw text if the response isn't valid JSON — e.g. an error page).
run_json() {
    local label="$1"; shift
    printf '```console\n$ %s\n```\n' "$label" >> "$S"
    echo "+ ${label}"
    local out formatted
    out=$("$@" 2>&1) || true
    [ -n "$out" ] && echo "$out"
    if formatted=$(printf '%s' "$out" | python3 -m json.tool 2>/dev/null); then
        printf '```json\n%s\n```\n\n' "$formatted" >> "$S"
    else
        printf '```\n%s\n```\n\n' "$out" >> "$S"
    fi
}
