from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from schemas.request_models import AgentState, RouteDecision
from actions.digital.n8n_tools import call_n8n_calendar, call_web_search
from langchain_core.messages import HumanMessage, AIMessage

GRAY = "\033[90m"

router_llm = ChatOllama(model="qwen2.5:1.5b", temperature=0, base_url="http://localhost:11434")
structured_router = router_llm.with_structured_output(RouteDecision)

# Use a slightly more creative temperature for general chat
chat_llm = ChatOllama(model="qwen2.5:1.5b", temperature=0.6, base_url="http://localhost:11434")

router_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are Cozmo, a strict routing supervisor.
Your ONLY job is to classify the user's request into exactly ONE route.

You MUST output a structured decision with one of these routes:
- "calendar"
- "web_search"
- "none"

---------------------
ROUTE DEFINITIONS:

1. "calendar"
Use this if the user:
- Mentions meetings, events, appointments, schedule
- Wants to create, update, move, or delete an event
- Asks what is on their calendar
Examples:
- "Do I have anything tomorrow?"
- "Schedule a meeting at 3pm"
- "Move my appointment to Friday"

2. "web_search"
Use this if the user:
- Asks for current or real-world information
- Mentions news, weather, sports, prices, or recent events
- Asks factual questions that may change over time
Examples:
- "What's the weather today?"
- "Latest news about AI"
- "Who won the game last night?"

3. "none"
Use this for:
- Casual conversation
- Opinions or general knowledge
- Questions about yourself
Examples:
- "Hi"
- "Tell me a joke"
- "Explain quantum physics"

---------------------
STRICT RULES:

- You MUST choose exactly one route.
- NEVER answer the question.
- NEVER explain your reasoning.
- NEVER hallucinate calendar data.
- If there is ANY doubt about real-time info → use "web_search".
- If there is ANY mention of scheduling → use "calendar".
- Default to "none" only if clearly general conversation.

---------------------
User input:
{user_input}
"""),
])

router_chain = router_prompt | structured_router


# ---GRAPH NODES ---
def route_query(state: AgentState):
    """The Supervisor: decides where to send the message."""
    last_message = state["messages"][-1].content
    decision = router_chain.invoke({"user_input": last_message})
    print(f"\n {GRAY} LangGraph Decision: {decision.route}")
    return {"next_route": decision.route}


def calendar_node(state: AgentState):
    """The Worker: Executes the n8n webhook."""
    last_message = state["messages"][-1].content
    n8n_reply = call_n8n_calendar(last_message)
    return {"messages": [AIMessage(content=n8n_reply)]}

def web_search_node(state: AgentState):
    """The Worker: Executes the n8n webhook."""
    last_message = state["messages"][-1].content
    print(f"{GRAY}Executing web search...")
    n8n_reply = call_web_search(last_message)
    if not n8n_reply:
        print(f"{GRAY}Warning: n8n returned None or empty string.")
        n8n_reply = "I tried to search the web, but I couldn't get a response from the search service."
    return {"messages": [AIMessage(content=n8n_reply)]}



def chat_node(state: AgentState):
    """The Fallback: Standard local conversation."""
    print(f"{GRAY}Routing to local chat...")
    response = chat_llm.invoke(state["messages"])
    return {"messages": [response]}


def decide_next_step(state: AgentState) -> str:
    route = state.get("next_route", "none")
    if route == "calendar":
        return "calendar_node"
    elif route == "web_search":
        return "web_search_node"
    return "chat_node"


# ---BUILD THE GRAPH ---
builder = StateGraph(AgentState)

builder.add_node("route_query", route_query)
builder.add_node("calendar_node", calendar_node)
builder.add_node("web_search_node", web_search_node)
builder.add_node("chat_node", chat_node)

builder.add_edge(START, "route_query")
builder.add_conditional_edges("route_query", decide_next_step)
builder.add_edge("calendar_node", END)
builder.add_edge("web_search_node", END)
builder.add_edge("chat_node", END)

cozmo_graph = builder.compile()


# Helper function to run the graph easily
def run_cozmo_agent(user_input: str) -> str:
    initial_state = {"messages": [HumanMessage(content=user_input)]}
    result = cozmo_graph.invoke(initial_state)
    return result["messages"][-1].content