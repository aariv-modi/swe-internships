#!/usr/bin/env bash
# Scrape once an hour for ITERATIONS hours, committing after each pass.
#
# Why a loop: GitHub's cron trigger is best-effort. On 2026-10-22 the "17 * * * *" schedule fired at
# 15:15, 19:13, 22:20 and 01:28 UTC, roughly every 3 hours. A long-lived job that sleeps between
# passes keeps the hourly cadence itself; the workflow then dispatches its own successor.
set -uo pipefail
ITERATIONS="${ITERATIONS:-5}"

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

push_with_retry() {
  for attempt in 1 2 3 4 5; do
    git pull --rebase --autostash -q && git push -q && return 0
    echo "push attempt $attempt failed; retrying"
    sleep $((attempt * 10))
  done
  return 1
}

for i in $(seq 1 "$ITERATIONS"); do
  start=$(date +%s)
  echo "=== pass $i/$ITERATIONS at $(date -u +'%H:%M UTC')"
  git pull --rebase --autostash -q || echo "pull failed; scraping current checkout"

  # Weekly: refresh the board registry from the community lists before scraping.
  cmd=scrape
  last=$(git log -1 --format=%ct --grep='^Refresh board registry' || true)
  if [ -z "$last" ] || [ $((start - last)) -gt $((7 * 86400)) ]; then
    cmd=all
  fi

  # A failed pass must not end the chain: log it and keep going.
  python -u -m scraper "$cmd" || echo "scraper exited with $?"

  git add README.md data/
  if ! git diff --cached --quiet; then
    if [ "$cmd" = all ]; then
      msg="Refresh board registry and update listings $(date -u +'%Y-%m-%d %H:%M UTC')"
    else
      msg="Update listings $(date -u +'%Y-%m-%d %H:%M UTC')"
    fi
    git commit -q -m "$msg"
    push_with_retry || echo "could not push this pass"
  fi

  if [ "$i" -lt "$ITERATIONS" ]; then
    wait=$((start + 3600 - $(date +%s)))
    if [ "$wait" -gt 0 ]; then
      echo "sleeping ${wait}s until the next pass"
      sleep "$wait"
    fi
  fi
done
