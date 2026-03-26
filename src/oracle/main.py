import os
import logging
import time
from pathlib import Path
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.security.api_key import APIKeyQuery
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_403_FORBIDDEN
from pydantic import BaseModel
from typing import Any, Optional

# Oracle imports
from .agent_system import OracleAgent, OracleConfig
# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Oracle Personal Agent Webhook")

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration Mapping (Bridge standard GCP env vars to OracleConfig)
if "GOOGLE_CLOUD_PROJECT" in os.environ and "GCP_PROJECT_ID" not in os.environ:
    os.environ["GCP_PROJECT_ID"] = os.environ["GOOGLE_CLOUD_PROJECT"]
if "GOOGLE_CLOUD_LOCATION" in os.environ and "GCP_LOCATION" not in os.environ:
    os.environ["GCP_LOCATION"] = os.environ["GOOGLE_CLOUD_LOCATION"]

# Ensure Skills directory for our personal agent tools
SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"
os.environ["ORACLE_SKILLS_DIR"] = str(SKILLS_DIR)

# Initialize Oracle Agent
agent: Optional[OracleAgent] = None
try:
    config = OracleConfig()
    agent = OracleAgent(config)
    logger.info("Oracle Agent initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Oracle Agent: {e}")

# API Key Authentication
api_key = os.environ.get("WEBHOOK_API_KEY")
if api_key:
    API_KEY = APIKeyQuery(name="api_key", auto_error=False)

    async def get_api_key(api_key_query: str = Depends(API_KEY)) -> str:
        if api_key_query != api_key:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials")
        return api_key_query

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/webhook")
async def dialogflow_webhook(request: Request) -> dict[str, Any]:
    """
    Handles POST requests from Dialogflow CX or Vertex AI Agent Builder.
    Uses OracleAgent for unified ReAct loop and tool orchestration.
    """
    req_data = await request.json()
    logger.info(f"Received Webhook Request: {req_data}")

    if not agent:
        return {"fulfillmentResponse": {"messages": [{"text": {"text": ["Agent is not configured."]}}]}}

    # 1. Parse payload
    user_input = req_data.get("text", "")
    session_info = req_data.get("sessionInfo", {})
    session_params = session_info.get("parameters", {})
    session_id = session_info.get("session", "default-session")

    if not user_input and "last_user_utterance" in session_params:
        user_input = session_params.get("last_user_utterance", "")

    # 2. Run Agent logic
    try:
        # OracleAgent handles persistence, history, and tools, including vision
        # if image_base64 is passed as part of the surrounding request context.
        # For Dialogflow specific image handling, we could enrich context here.
        agent_response = agent.run(user_input, session_id=session_id)
        reply_text = agent_response
    except Exception as e:
        logger.error(f"Oracle Agent Error: {e}")
        reply_text = "I'm having a little trouble connecting to my brain right now. Please try again in a moment."

    # 3. Format Fulfillment Response
    return {
        "fulfillmentResponse": {"messages": [{"text": {"text": [reply_text]}}]},
        "sessionInfo": {"parameters": session_params},
    }


class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None


class ChatResponse(BaseModel):
    thread_id: str
    response: str


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    Unified chat endpoint leveraging OracleAgent's memory and state management.
    """
    if not agent:
        raise HTTPException(status_code=500, detail="Oracle Agent not initialized")

    thread_id = request.thread_id or f"thread_{int(time.time() * 1000)}"

    try:
        # OracleAgent.run automatically handles history lookup/persistence by session_id
        response = agent.run(request.message, session_id=thread_id)
    except Exception as e:
        logger.error(f"Chat execution error: {e}")
        response = "I encountered an error processing your request."

    return ChatResponse(thread_id=thread_id, response=response)


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint for monitoring."""
    status = "healthy" if agent else "degraded"
    return {
        "status": status,
        "service": "personal-agent-webhook",
        "agent_type": "OracleAgent",
        "model": agent.cfg.model_id if agent else "none",
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
