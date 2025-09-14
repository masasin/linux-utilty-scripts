#!/bin/bash
#
# Automatically chooses 'docker-compose run' or 'docker-compose exec'.

if [ "$#" -lt 1 ]; then
  printf 'Usage: dcr <service> [command...]\n' >&2
  exit 1
fi

service=$1
shift

# Check if the service container is running, without printing output (>/dev/null)
if docker compose ps -q "$service" | grep -q .; then
  # If running, exec into it
  docker compose exec "$service" "$@"
else
  # If not running, run it with port mapping
  docker compose run --rm --service-ports "$service" "$@"
fi
