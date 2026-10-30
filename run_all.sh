#!/usr/bin/env bash
# Kills any stale processes on the 5 agent ports, then starts all 5 agents
# in the background. Logs go to ./.logs/<agent>.log, PIDs to ./.pids/<agent>.pid.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

HOST_AGENT_PORT="${HOST_AGENT_PORT:-8000}"
FLIGHT_AGENT_PORT="${FLIGHT_AGENT_PORT:-8001}"
RESEARCH_AGENT_PORT="${RESEARCH_AGENT_PORT:-8002}"
ACCOMMODATION_FOOD_AGENT_PORT="${ACCOMMODATION_FOOD_AGENT_PORT:-8003}"
ITINERARY_AGENT_PORT="${ITINERARY_AGENT_PORT:-8004}"

mkdir -p .logs .pids

kill_stale() {
  local port="$1"
  local pid
  if command -v lsof >/dev/null 2>&1; then
    pid=$(lsof -ti "tcp:${port}" 2>/dev/null || true)
  else
    # lsof isn't installed on every distro (e.g. WSL); fuser is the fallback.
    pid=$(fuser -n tcp "${port}" 2>/dev/null | xargs || true)
  fi
  if [ -n "${pid}" ]; then
    echo "Killing stale process on port ${port} (pid ${pid})"
    kill -9 ${pid} 2>/dev/null || true
  fi
}

for port in "$HOST_AGENT_PORT" "$FLIGHT_AGENT_PORT" "$RESEARCH_AGENT_PORT" \
            "$ACCOMMODATION_FOOD_AGENT_PORT" "$ITINERARY_AGENT_PORT"; do
  kill_stale "$port"
done

start_agent() {
  local name="$1"
  local module="$2"
  local port="$3"
  echo "Starting ${name} on port ${port}..."
  nohup .venv/bin/uvicorn "${module}:app" --host 0.0.0.0 --port "${port}" \
    > ".logs/${name}.log" 2>&1 &
  echo $! > ".pids/${name}.pid"
}

start_agent "flight_agent" "agents.flight_agent.__main__" "$FLIGHT_AGENT_PORT"
start_agent "research_agent" "agents.research_agent.__main__" "$RESEARCH_AGENT_PORT"
start_agent "accommodation_food_agent" "agents.accommodation_food_agent.__main__" "$ACCOMMODATION_FOOD_AGENT_PORT"
start_agent "itinerary_agent" "agents.itinerary_agent.__main__" "$ITINERARY_AGENT_PORT"
start_agent "host_agent" "agents.host_agent.__main__" "$HOST_AGENT_PORT"

echo ""
echo "All 5 agents starting. Tail logs with: tail -f .logs/*.log"
echo "Stop everything with: kill \$(cat .pids/*.pid)"
