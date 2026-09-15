#!/usr/bin/env bash
# Local Docker build helper.
# Usage:
#   ./scripts/docker_build.sh             # build only (tag: local)
#   TAG=1.2.3 ./scripts/docker_build.sh   # build with custom tag
#   ./scripts/docker_build.sh --push      # build and push to GHCR
set -euo pipefail

IMAGE="ghcr.io/albauer-priv/rps"
TAG="${TAG:-local}"

docker build -t "$IMAGE:$TAG" .

if [[ "${1:-}" == "--push" ]]; then
    docker push "$IMAGE:$TAG"
fi
