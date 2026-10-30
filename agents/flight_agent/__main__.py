from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

import uvicorn

from common.a2a_server import create_app

from .task_manager import handle_task

app = create_app("flight_agent", handle_task)

if __name__ == "__main__":
    port = int(os.getenv("FLIGHT_AGENT_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
