# SmartItin: Multi-Agent A2A Travel Planner

## Credits

SmartItin replicates the concept and architecture of **travAI** by
Carlos Alberto Lembono
([LinkedIn](https://www.linkedin.com/in/carlosalbertolembono)), adapted
to run on the OpenAI API instead of Gemini.

A trip planner built as 5 independent FastAPI microservices ("agents") that
coordinate over plain JSON-over-HTTP, plus a React frontend. It uses the users' input:
origin, destination, dates, theme, budget tier, and a total budget to
searche for flights, hotels, restaurants, and attractions
(via SerpAPI), then has an LLM assemble a day-by-day itinerary that targets
your budget.

## Key Features

- **Multiple agents working together**: instead of one
  general-purpose AI doing everything, a dedicated agent handles each part
  of the trip, one for flights, one for destination research, one for
  hotels & food, one for building the itinerary, coordinated by a
  central planner agent. Each agent focuses on just its own job, which
  means more accurate, relevant results per category than a single AI
  trying to juggle all of it at once.
- **Real search results**: flights, hotels, restaurants,
  and attractions all come from live Google Flights / Google Maps / Google
  Search data, with working booking and maps links.
- **Budget-aware planning**: enter one total trip budget, and the app
  figures out how to split it across flights, hotel, food, and activities
  based on your specific trip (e.g. a tight flight budget paired with a
  5-star hotel choice is recognized as "willing to spend more on lodging").
- **Editable itinerary**: add a suggested nearby extension to your trip,
  or apply an AI-suggested alternative, and the plan updates instantly.
- **Downloadable trip plan**: export the full plan as a PDF, or share a
  link to the results page.

## Tech Stack

- **Frontend**: React 19, Vite, TypeScript, Tailwind CSS v4, React Router,
  `@react-pdf/renderer` (PDF export), hand-built SVG icon set.
- **Backend/API**: Python, FastAPI, Uvicorn, 5 independent microservices
  ("agents") coordinated over plain JSON-over-HTTP (a minimal, custom
  A2A-style protocol, not a message queue or shared database).
- **AI Engine**: Google ADK (Agent Development Kit): multi-agent
  orchestration with a gatherer/formatter pattern (free-form tool-using
  research, then schema-enforced JSON output). LLM: OpenAI API via
  LiteLLM (default `gpt-4o-mini`, changeable with `LLM_MODEL` in `.env`).
- **Search/Data**: SerpAPI: Google Flights, Google Maps, and Google
  Search engines for real prices, real places, and real photos (no
  AI-invented links or images).
- **Storage**: no database: an in-memory job store for the async trip
  pipeline, plus a disk-persisted JSON TTL cache for research/hotel
  results.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 User Interface (React + Vite)                   │
│  - Input: Origin, Destination, Dates, Theme, Budget, Pace       │
│  - Output: Flights, Guide, Stay & Food, Itinerary, Cost Summary │
└────────────────────────────┬────────────────────────────────────┘
                             │  POST /run-async, GET /status/:id
                             ▼
┌────────────────────────────────────────────────────────────────┐
│                       Host Agent (:8000)                       │
│      Orchestration Layer — job store, budget allocation,       │
│              flight x hotel combination scoring                │
└──┬─────────────┬─────────────┬─────────────┬───────────────────┘
   │             │             │             │
   ▼             ▼             ▼             ▼
┌────────┐   ┌──────────┐  ┌──────────┐  ┌───────────┐
│ Flight │   │ Research │  │  Accom-  │  │ Itinerary │
│ Agent  │   │  Agent   │  │modation &│  │  Agent    │
│ :8001  │   │  :8002   │  │Food Agent│  │  :8004    │
│        │   │          │  │  :8003   │  │           │
└───┬────┘   └────┬─────┘  └────┬─────┘  └─────┬─────┘
    │             │             │              │
    ▼             ▼             ▼              ▼
┌────────────────────────────────────────────────────────────────┐
│                   External APIs & Tools                        │
│  - SerpAPI: Google Flights, Google Maps, Google Search         │
│  - LLM: OpenAI API (gpt-4o-mini by default) via LiteLLM        │
└────────────────────────────────────────────────────────────────┘
```

**Request flow for one trip:**

1. Frontend calls `POST /run-async` on Host Agent → a job is created and a
   `job_id` returned immediately; the real work runs in the background.
2. Host Agent calls Flight, Research, and Accommodation & Food agents in
   parallel (`asyncio.as_completed`), plus its own in-process budget
   allocation judgment call, each result is written into the job as soon
   as it lands.
3. The frontend polls `GET /status/:job_id` every 2s; each poll reflects
   whichever sections are done so far, so the UI resolves one skeleton at a
   time instead of blocking on the whole ~100s pipeline.
4. Once Flight and Accommodation & Food are both back, Host Agent scores
   every flight x hotel combination (`common/budget_optimizer.py`) and
   marks the best-fit pair `selected: true`.
5. Itinerary Agent is called last (it needs Research + Accommodation as
   context) with the remaining food/activity budget as a soft spending
   target, then a cost summary is built and the job is marked `done`.
6. Editing the itinerary afterward (adding a trip extension, applying a
   modify-suggestion) goes through a separate, much cheaper
   `POST /modify-itinerary` call that reuses the job's already-fetched
   context instead of re-running the whole pipeline.

## Agents

**Host Agent**: the orchestrator, owns the job store, fans out to the other 4 agents, judges a low/medium/high spending priority per category from the trip's specifics  e.g. an economy tier paired with a 5-star hotel choice signals "compromise on flights, not lodging", and picks the best flight+hotel combination once both are back. Also handles itinerary edits after the initial plan.

**Flight Agent**: real-time round-trip
flight search via SerpAPI's Google Flights engine then returns the cheapest outbound paired with its top 3 real return options.

**Research Agent**: destination
research: why visit, climate/weather, culture notes, safety tips, top
attractions, and hidden gems, via SerpAPI web + Maps search.

**Accommodation & Food Agent**: hotel and restaurant search matching the requested star rating and the budget tier's dining style.

**Itinerary Agent**: creates the day-by-day plan from Research + Accommodation context, respecting the trip's travel pace (relaxed vs. packed) and the food/activity budget targets handed down by Host Agent. Also handles post-plan edits (adding an
extension, applying a modify-suggestion) in a separate mode.

## Project Structure

```
a2a_travel_planner/
├── agents/
│   ├── host_agent/            # Orchestrator (:8000)
│   │   ├── __main__.py        # FastAPI app: /run-async, /status/:id, /modify-itinerary
│   │   ├── agent.py           # budget_allocation_agent (priority judgment)
│   │   ├── jobs.py            # In-memory job store
│   │   └── task_manager.py    # Fan-out, combo scoring, itinerary-modify handling
│   ├── flight_agent/          # :8001 — real-time round-trip flight search
│   ├── research_agent/        # :8002 — destination guide + attractions
│   ├── accommodation_food_agent/  # :8003 — hotels + restaurants
│   ├── itinerary_agent/       # :8004 — day-by-day plan (create + modify modes)
│   └── (each leaf agent: __main__.py, agent.py, task_manager.py)
│
├── common/                    # Shared code used across all 5 agents
│   ├── schemas.py             # Every request/response shape (Pydantic)
│   ├── a2a_server.py          # Wraps a handler into a FastAPI app
│   ├── a2a_client.py          # HTTP client Host Agent uses to call other agents
│   ├── adk_runner.py          # Runs one LLM turn via google-adk, retry+backoff
│   ├── llm_config.py          # Resolves which LLM provider/model to use
│   ├── serpapi_tools.py       # Shared SerpAPI search functions
│   ├── cache.py               # Disk-persisted TTL cache
│   ├── budget_optimizer.py    # Priority → percentage math, combo scoring
│   └── tiers.py               # Economy/standard/luxury tier defaults
│
├── frontend/
│   └── src/
│       ├── pages/             # TripInputPage, ResultsPage
│       ├── components/        # One *Content.tsx per results section,
│       │                      # + TripPlanPdf.tsx, icons, form inputs
│       ├── hooks/             # useTripPoll, usePageTitle
│       ├── api.ts             # All calls to Host Agent
│       ├── types.ts           # Mirrors common/schemas.py
│       └── tiers.ts           # Mirrors common/tiers.py
│
├── run_all.sh                 # Starts all 5 agents in the background
├── requirements.txt           # Python dependencies
└── .env.example               # API keys, ports, provider config
```

## Setup

### Prerequisites

- Python 3.11+
- Node 18+
- An [OpenAI API](https://platform.openai.com/api-keys) key
- A [SerpAPI](https://serpapi.com/) key (powers all real flight/hotel/place
  search — has a limited free tier, be mindful of quota during development)

### Backend

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in your API keys, see comments in the file
```

`.env` holds `OPENAI_API_KEY`, the OpenAI model (`LLM_MODEL`, default
`gpt-4o-mini`), `SERPAPI_API_KEY`, and each agent's port.

Start all 5 agents:

```bash
bash run_all.sh
```

This kills anything already bound to ports 8000-8004, then starts each
agent in the background. Logs: `.logs/<agent>.log`. Stop everything with
`kill $(cat .pids/*.pid)`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens on `http://localhost:5173` by default, and talks to Host Agent at
`VITE_API_URL` (defaults to `http://localhost:8000`, set in `.env`). This
is the primary way to use the app, fill in the trip form and watch the
results page fill in progressively.

### Trying the backend directly (without the frontend)

```bash
curl -s http://localhost:8000/run \
  -H 'content-type: application/json' \
  -d '{
    "origin": "Jakarta",
    "destination": "Bali",
    "start_date": "2026-08-10",
    "end_date": "2026-08-14",
    "theme": "couple getaway",
    "budget_tier": "standard",
    "flight_class": "premium_economy",
    "hotel_stars": 4,
    "total_budget_idr": 15000000,
    "travel_pace": "relaxed"
  }' | python3 -m json.tool
```

This calls the synchronous `/run` endpoint (waits for the whole ~100s
pipeline before responding) — useful for quick backend testing. The
frontend instead uses `/run-async` + polling, so the UI doesn't block.

Each agent also exposes `GET /health` on its own port (8000-8004) as a
lightweight liveness check.

### Ports

| Agent | Port |
|---|---|
| Host | 8000 |
| Flight | 8001 |
| Research | 8002 |
| Accommodation & Food | 8003 |
| Itinerary | 8004 |
| Frontend (Vite dev server) | 5173 |
