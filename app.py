"""Vercel/WSGI entrypoint for the Oracle GUI."""

from __future__ import annotations

import logging
from threading import Lock

from gui import app as gui_app

logger = logging.getLogger(__name__)

app = gui_app.app
_bootstrap_lock = Lock()
_bootstrap_state = {"attempted": False}

gui_app.create_gui_directories()


def ensure_agent_initialized() -> None:
    if gui_app.app_state.agent is not None:
        return

    with _bootstrap_lock:
        if gui_app.app_state.agent is not None or _bootstrap_state["attempted"]:
            return

        _bootstrap_state["attempted"] = True
        if not gui_app.initialize_agent():
            logger.warning(
                "Oracle Agent failed to initialize during WSGI startup; GUI will run in degraded mode"
            )


@app.before_request
def bootstrap_oracle_agent() -> None:
    ensure_agent_initialized()
