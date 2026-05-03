from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from schemas.request_models import AgentState, RouteDecision
from actions.n8n_tools import call_n8n_calendar
from langchain_core.messages import HumanMessage, AIMessage

router_llm = ChatOllama(model="qwen2.5:1.5b", temperature=0, base_url="http://localhost:11434")
structured_router = router_llm.with_structured_output(RouteDecision)

# Use a slightly more creative temperature for general chat
chat_llm = ChatOllama(model="qwen2.5:1.5b", temperature=0.6, base_url="http://localhost:11434")

router_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are Cozmo, an intelligent routing supervisor.
    Read the user's input and decide the correct route.

    ROUTES:
    - 'calendar': Use if the user asks to check their schedule, create a meeting, move/update an event, or delete an event.
    - 'none': Use for general conversation, small talk, or questions about yourself.

    RULES:
    1. NEVER answer calendar questions directly.
    2. NEVER hallucinate schedule details. Always route to 'calendar'."""),
    ("human", "{user_input}")
])

router_chain = router_prompt | structured_router


# ---GRAPH NODES ---
def route_query(state: AgentState):
    """The Supervisor: decides where to send the message."""
    last_message = state["messages"][-1].content
    decision = router_chain.invoke({"user_input": last_message})
    print(f" LangGraph Decision: {decision.route}")
    return {"next_route": decision.route}


def calendar_node(state: AgentState):
    """The Worker: Executes the n8n webhook."""
    last_message = state["messages"][-1].content
    n8n_reply = call_n8n_calendar(last_message)
    return {"messages": [AIMessage(content=n8n_reply)]}


def chat_node(state: AgentState):
    """The Fallback: Standard local conversation."""
    print(" Routing to local chat...")
    response = chat_llm.invoke(state["messages"])
    return {"messages": [response]}


def decide_next_step(state: AgentState) -> str:
    route = state.get("next_route", "none")
    if route == "calendar":
        return "calendar_node"
    return "chat_node"


# ---BUILD THE GRAPH ---
builder = StateGraph(AgentState)

builder.add_node("route_query", route_query)
builder.add_node("calendar_node", calendar_node)
builder.add_node("chat_node", chat_node)

builder.add_edge(START, "route_query")
builder.add_conditional_edges("route_query", decide_next_step)
builder.add_edge("calendar_node", END)
builder.add_edge("chat_node", END)

cozmo_graph = builder.compile()


# Helper function to run the graph easily
def run_cozmo_agent(user_input: str) -> str:
    initial_state = {"messages": [HumanMessage(content=user_input)]}
    result = cozmo_graph.invoke(initial_state)
    return result["messages"][-1].content