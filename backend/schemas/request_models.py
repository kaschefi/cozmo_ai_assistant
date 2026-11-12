from typing import TypedDict, Annotated, List, Optional, Dict, Any, Literal
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    next_route: str
    active_tools: List[dict]
    retrieved_memories: List[str] # LONG-TERM CONTEXT INJECTION
    retrieved_documents: List[dict] # GROUNDED DOCUMENT KNOWLEDGE
    rag_only: bool
    document_namespace: Optional[str]
    summary: str
    provider: str # "local" (Ollama) or "cloud" (Azure GPT-4.1 Nano)
    pending_interrupt: Optional[Dict[str, Any]]
    mcp_active_servers: List[str]
    resumed_from_interrupt: bool
    tool_call_args: Optional[Dict[str, Any]]

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
    rag_only: bool = Field(
        default=False,
        description="When True, bypasses tool retrieval/routing and answers directly via Document RAG."
    )
    document_namespace: Optional[str] = Field(
        default=None,
        description="Optional Semantic ETL namespace to scope document retrieval."
    )


class HITLInterruptPayload(BaseModel):
    interrupt_type: Literal["mcp_discovery", "mutating_tool"] = "mcp_discovery"
    server_pack_id: Optional[str] = None
    tool_name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    proposed_args: Optional[Dict[str, Any]] = None
    message: str


class ResumeChatRequest(BaseModel):
    session_id: str = Field(..., description="Active LangGraph thread session ID to resume.")
    approved: bool = Field(..., description="Whether user approved adding the tool/MCP pack.")
    modified_args: Optional[Dict[str, Any]] = Field(default=None, description="Optional parameter overrides.")
    provider: Optional[str] = Field(default="local", description="Model provider.")
    mute: Optional[bool] = Field(default=False, description="Audio mute flag.")


class MCPRegisterRequest(BaseModel):
    pack_id: str = Field(..., description="Unique MCP pack identifier, e.g. 'mcp_pack_custom'.")
    display_name: str = Field(..., description="Human-readable server name.")
    description: str = Field(..., description="Semantic description of server capabilities.")
    command: str = Field(default="npx", description="Execution command: 'npx', 'uvx', etc.")
    args: List[str] = Field(default_factory=list, description="CLI arguments.")
    env_vars: List[str] = Field(default_factory=list, description="Required environment variable names.")
    default_destructive_tools: List[str] = Field(default_factory=list, description="Known mutating tools.")
    destructive_regex: Optional[str] = Field(default=None, description="Regex pattern matching mutating tool names.")


class MCPDisconnectRequest(BaseModel):
    pack_id: str = Field(..., description="Unique MCP pack identifier to disconnect, e.g. 'mcp_pack_github'.")


class MCPConnectRequest(BaseModel):
    pack_id: str = Field(..., description="Unique MCP pack identifier to connect, e.g. 'mcp_pack_github'.")
