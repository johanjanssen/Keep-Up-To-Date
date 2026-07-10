#!/usr/bin/env bash
# exercise-endpoints.sh — Call the app endpoints to generate coverage data.
# Deliberately skips /admin/diagnostics — keeps it RED (0%) in the report.
set -euo pipefail
BASE_URL="http://localhost:8080"
echo ""
echo "============================================================"
echo "  JaCoCo Demo — Exercising endpoints"
echo "============================================================"
echo ""
if ! curl -sf "${BASE_URL}/hello" -o /dev/null 2>/dev/null; then
    echo "ERROR: App not responding at ${BASE_URL}."
    echo "       Start it first: bash scripts/start-with-agent.sh"
    exit 1
fi
call() {
    local METHOD="$1" URL="$2"; shift 2
    printf "  %-4s  %s\n        " "${METHOD}" "${URL}"
    if [[ "${METHOD}" == "POST" ]]; then
        curl -sf -X POST -H "Content-Type: application/json" "$@" "${URL}"
    else
        curl -sf "${URL}"
    fi
    echo ""
}
echo "-- /hello --------------------------------------------------"
call GET  "${BASE_URL}/hello"
call GET  "${BASE_URL}/hello?name=Alice"
call GET  "${BASE_URL}/hello?name=Bob"
echo "-- /users --------------------------------------------------"
call POST "${BASE_URL}/users" -d '{"name":"Alice","email":"alice@example.com"}'
call POST "${BASE_URL}/users" -d '{"name":"Bob","email":"bob@example.com"}'
call POST "${BASE_URL}/users" -d '{"name":"Carol","email":"carol@example.com"}'
call GET  "${BASE_URL}/users"
call GET  "${BASE_URL}/users/1"
call GET  "${BASE_URL}/users/2"
echo "-- /users/{id} 404 branch ----------------------------------"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/users/999")
printf "  GET   %s/users/999  ->  HTTP %s (expected 404)\n\n" "${BASE_URL}" "${STATUS}"
echo "-- /admin/diagnostics — intentionally SKIPPED -------------"
echo "   Will appear RED / 0% in the coverage report"
echo ""
echo "------------------------------------------------------------"
echo "OK  Endpoints exercised."
echo "    Stop the app (Ctrl+C) then: bash scripts/generate-report.sh"
echo "------------------------------------------------------------"
echo ""
