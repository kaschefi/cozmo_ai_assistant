from typing import TypedDict, Annotated, List
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    next_route: str
    active_tools: List[dict]
    retrieved_memories: List[str] # LONG-TERM CONTEXT INJECTION
    summary: str
    provider: str # "local" (Ollama) or "cloud" (Azure GPT-4.1 Nano)

# The Structured Output for the LLM
class RouteDecision(BaseModel):
    route: str = Field(description="The exact name of the tool node to execute, or 'none' if it's general chat.")

class MoveRequest(BaseModel):
    distance: float = Field(
        ...,
        description="The distance in millimeters to drive forward (positive) or backward (negative)."
    )
    speed: float = Field(
        default=50.0,
        ge=10,
        le=200,
        description="The speed to drive in mm/s. Default is 50."
    )

class SpeakRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=250,
        description="The text you want Cozmo to say out loud."
    )
    play_animation: bool = Field(
        default=True,
        description="If true, Cozmo will act out the speech with animations."
    )
    language: str = Field(
        default="fa",
        description="The language of the speech. Default is persian."
    )

class HeadRequest(BaseModel):
    angle: float = Field(
        ...,
        ge=-25,
        le=44.5,
        description="The angle in degrees to move the head. Range is approx -25 (down) to 45 (up)."
    )

class LiftRequest(BaseModel):
    height: float = Field(
        ...,
        ge=0,
        le=1,
        description="The height of the lift from 0.0 (bottom) to 1.0 (top)."
    )

class TimerRequest(BaseModel):
    seconds: int


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        description="The chat message input from the frontend user."
    )
    session_id: str = Field(
        default="web_session",
        description="Thread ID mapping for LangGraph memory states."
    )
    mute: bool = Field(
        default=False,
        description="If True, the agent will only output text response and not speak."
    )
    provider: str = Field(
        default="local",
        description="Model execution provider: 'local' (Ollama) or 'cloud' (Azure GPT-4.1 Nano for Chat & Calendar/Todoist)."
    )