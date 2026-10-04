#!/usr/bin/env bash
# Report which container runtime is available, its version, and what it can do.
#
# Day 19's Docker path needs three services (Qdrant + Redis + Postgres). There
# are now three plausible runtimes on a student laptop, and they are NOT
# interchangeable -- Apple's `container` has no compose implementation, so the
# same docker-compose.yml simply does not apply to it.
#
# Run:  bash scripts/runtime-check.sh   (or `make runtime-check`)
# Always exits 0: this is a report, not a gate.

set -uo pipefail

bold() { printf '\033[1m%s\033[0m\n' "$1"; }
row()  { printf '  %-22s %s\n' "$1" "$2"; }

bold "Day 19 — container runtime check"
row "host" "$(uname -s) $(uname -r) / $(uname -m)"
if command -v sw_vers >/dev/null 2>&1; then
  row "macOS" "$(sw_vers -productVersion 2>/dev/null)"
fi
echo

HAVE_DOCKER=0; HAVE_COMPOSE=0; HAVE_PODMAN=0; HAVE_APPLE=0

# ── Docker ──────────────────────────────────────────────────────────────
bold "docker"
if command -v docker >/dev/null 2>&1; then
  HAVE_DOCKER=1
  row "version" "$(docker --version 2>&1 | head -1)"
  if docker compose version >/dev/null 2>&1; then
    HAVE_COMPOSE=1
    row "compose v2" "$(docker compose version 2>&1 | head -1)"
  else
    row "compose v2" "MISSING (need Docker Desktop >= 4.x)"
  fi
  if docker info >/dev/null 2>&1; then
    row "daemon" "running"
  else
    row "daemon" "NOT running — start Docker Desktop"
    HAVE_COMPOSE=0
  fi
else
  row "version" "not installed"
fi
echo

# ── Podman ──────────────────────────────────────────────────────────────
bold "podman"
if command -v podman >/dev/null 2>&1; then
  HAVE_PODMAN=1
  row "version" "$(podman --version 2>&1 | head -1)"
  if podman compose version >/dev/null 2>&1 || command -v podman-compose >/dev/null 2>&1; then
    row "compose" "available"
  else
    row "compose" "missing (install podman-compose)"
  fi
else
  row "version" "not installed"
fi
echo

# ── Apple container (github.com/apple/container) ────────────────────────
bold "apple container"
if command -v container >/dev/null 2>&1; then
  HAVE_APPLE=1
  row "version" "$(container --version 2>&1 | head -1)"
  STATUS=$(container system status 2>&1 | awk '/^status/{print $2}')
  row "system service" "${STATUS:-unknown}"
  row "compose support" "NONE — use scripts/container-up.sh instead"
  if [ "${STATUS:-}" != "running" ]; then
    row "hint" "run: container system start"
  fi
else
  row "version" "not installed"
  row "note" "Apple silicon + macOS 26+ only — https://github.com/apple/container"
fi
echo

# ── Verdict ─────────────────────────────────────────────────────────────
bold "recommended path"
if [ "$HAVE_COMPOSE" = "1" ]; then
  echo "  bash setup-docker.sh        # docker compose (3 services, one file)"
elif [ "$HAVE_APPLE" = "1" ]; then
  echo "  make container-up           # Apple container (no compose; one run per service)"
  echo "  then: bash setup-docker.sh  # it detects the running services"
elif [ "$HAVE_PODMAN" = "1" ]; then
  echo "  podman compose up -d        # then: bash setup-docker.sh"
else
  echo "  bash setup-lite.sh          # no container runtime found — the lite path"
  echo "  (lite covers every graded criterion; Docker is an optional upgrade)"
fi
