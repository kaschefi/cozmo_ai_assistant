# core/routing/layer2/graph_nodes.py
import re
import threading
import sys
from typing import List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, RemoveMessage
from langsmith import traceable

import os
os.environ["USE_TF"] = "0"
import laya

from core.routing.llm_factory import get_llm
from core.routing.layer2.tool_vector_db import tool_rag_registry
from schemas.memory_db import long_term_memory
from schemas.request_models import AgentState, RouteDecision

GRAY = "\033[90m"
RESET = "\033[0m"

_LAYA_AGENT = None
_LAYA_LOCK = threading.Lock()

def get_laya_agent(model_id: str = "convaiinnovations/laya-typed-decisions"):
    global _LAYA_AGENT
    if _LAYA_AGENT is None:
        with _LAYA_LOCK:
            if _LAYA_AGENT is None:
                print(f"[LayaRouter] Pre-loading LAYA Typed Decision Model '{model_id}'...")
                _LAYA_AGENT = laya.load(model_id)
                print("[LayaRouter] LAYA Decision Model initialized successfully.")
    return _LAYA_AGENT
chat_llm = get_llm("CHAT_LLM_MODEL", "gemma4:e2b", temperature=0.6)


def is_conversational_query(text: str) -> bool:
    """
    Detects whether user input is purely conversational greeting, acknowledgment, or chit-chat.
    Ensures casual chat prompts bypass tool RAG matching and route straight to chat_node.
    """
    if not text:
        return True
    t = text.strip().lower()
    t_clean = re.sub(r'[^\w\s]', '', t)
    words = t_clean.split()
    if not words:
        return True

    GREETINGS = {
        "hi", "hello", "hey", "hiya", "howdy", "greetings", "yo", "sup",
        "good morning", "good afternoon", "good evening", "good night",
        "how are you", "how are you doing", "hows it going", "how are things",
        "whats up", "what is up", "who are you", "what can you do", "introduce yourself",
        "nice to meet you", "pleased to meet you",
        "thanks", "thank you", "ok", "okay", "cool", "bye", "goodbye"
    }
    if t_clean in GREETINGS:
        return True
    if len(words) <= 2 and words[0] in {"hi", "hello", "hey", "hiya", "yo"}:
        return True
    return False


_SETUP_EXCLUSION_NAMES = ("setup_gaming", "setup_study", "setup_coding")


def is_file_operation_query(text: str) -> bool:
    """
    Detects whether user input is requesting workspace file or directory manipulation
    (e.g. creating, making, writing, editing, modifying, reading, viewing, deleting files or directories).
    Used to prevent workstation IDE launchers (setup_coding) from intercepting file operations.
    """
    if not text:
        return False
    t = text.lower()
    # Check for workspace file extension with common file manipulation verbs
    ext_pattern = r'\b(?:make|create|write|edit|modify|update|delete|remove|read|view|touch|append|show|inspect)\b.*?\b[\w\-_\.]+\.(?:md|py|txt|json|csv|js|ts|html|css|yaml|yml|xml|log|sh|bat)\b'
    if re.search(ext_pattern, t):
        return True
    # Mutating verbs or explicit code/folder nouns always denote filesystem operations
    mutating_or_fs_pattern = r'\b(?:make|create|write|edit|modify|update|delete|remove|touch|append)\b.*?\b(?:fi+l+e*s?|document|script|directory|folder)\b'
    if re.search(mutating_or_fs_pattern, t):
        return True
    read_fs_pattern = r'\b(?:read|view|inspect|list)\b.*?\b(?:fi+l+e*s?|script|directory|folder)\b'
    if re.search(read_fs_pattern, t):
        return True
    # Read-only 'document' phrasing is a workspace file op only when not referring to uploaded RAG docs
    if re.search(r'\b(?:read|view|inspect)\b.*?\bdocument\b', t) and not re.search(
        r'\b(?:uploaded|indexed|knowledge\s+base|pdf|docx|thesis|srs)\b', t
    ):
        return True
    # Check for 'file called/named ...'
    if re.search(r'\bfi+l+e*s?\s+(?:called|named)\b', t):
        return True
    return False


def is_workstation_setup_query(text: str) -> bool:
    """
    Detects whether user query is an explicit command to launch workstation application setups
    (setup_gaming, setup_study, setup_coding).
    Excludes file operations, document/specification inquiries, and non-launch questions.
    """
    if not text:
        return False
    if is_file_operation_query(text):
        return False

    t = text.strip().lower()

    # Reject if it mentions document/RAG/specification artifacts
    if re.search(r'\b(?:srs|requirement|requirements|specification|specifications|specs|document|documents|doc|docs|pdf|docx|paper|thesis|uploaded|knowledge\s+base|conclusions?|summary)\b', t):
        return False

    # Reject pure informational/summary phrasing unless it explicitly commands launching an app/setup
    explicit_launch_cue = re.search(
        r'\b(?:open|launch|boot|start|prepare|set\s*up|configure|ready|bring\s+up)\b.*?\b(?:steam|discord|moodle|notebooklm|pycharm|gaming\s+(?:mode|setup|environment)|study\s+(?:mode|setup|session|tabs|materials)|coding\s+(?:mode|setup|workspace)|workstation|laptop|pc|computer|browser)\b',
        t
    )
    if re.match(r'^(summarize|summarise|explain|describe|tell me about)\b', t):
        return False
    if (t.endswith("?") or re.match(r'^(what|how|why|who|when|which|where|is |are |does |do )\b', t)) and not explicit_launch_cue:
        return False

    setup_patterns = [
        r'\b(?:gaming|game|study|studying|coding|code|programming|dev)\s+(?:mode|setup|time|work|environment|session|workspace)\b',
        r'\b(?:set|prepare|configure|ready|get)\b.*?\b(?:laptop|pc|workstation|computer|screen|browser|workspace|environment)\b.*?\b(?:gaming|game|counter-strike|study|studying|research|homework|coding|code|programming|software|development)\b',
        r'\b(?:open|launch|boot|start|bring\s+up)\b.*?\b(?:steam|discord|moodle|notebooklm|pycharm|study\s+materials|study\s+tabs|academic\s+tabs|programming\s+tools|github)\b',
        r'\btime to (?:game|study|code)\b',
        r'\b(?:i want to|let\'?s|start)\s+(?:game|play\b.*\bgames|study|studying|code|coding)\b',
        r'^setups?\s+(?:game|gaming|study|code|coding)$',
    ]
    return any(re.search(p, t) for p in setup_patterns)


def is_document_qa_query(text: str, retrieved_documents: Optional[List[dict]] = None) -> bool:
    """
    Detects queries specifically targeting uploaded/indexed RAG documents rather than
    external action tools (weather, web search, calendar, todoist, code sandbox, or workspace files).
    Avoids blocking general question words ('what', 'how', 'who', 'list', '?') so tool routing stays intact.
    """
    if not text or is_file_operation_query(text) or is_workstation_setup_query(text):
        return False
    t = text.strip().lower()

    # Never hijack explicit action/tool requests even if document terms appear (e.g. "add a task to review the SRS")
    explicit_tool_cues = [
        r'\b(?:todo|to-do|task|tasks|checklist)\b',
        r'\b(?:calendar|schedule|reschedule|meeting|appointment|event|standup|agenda)\b',
        r'\b(?:weather|forecast|temperature|rain|raining|snow|snowing|wind|storm)\b',
        r'\b(?:search\s+(?:the\s+)?web|google|web\s+search|breaking\s+news|stock\s+price|market\s+cap|champions\s+league)\b',
        r'\b(?:run|execute)\b.*?\b(?:code|python|script)\b',
        r'\b(?:calculate|compute|square\s+root|power\s+of)\b',
        r'\b(?:move|drive|turn|dock|sweep|charger)\b',
    ]
    if any(re.search(p, t) for p in explicit_tool_cues):
        return False

    # Strong explicit uploaded-document / specification Q&A patterns
    if re.search(
        r'\b(?:uploaded|knowledge\s+base|srs|thesis|dissertation|manuscript|pdf|docx|must\s+requirements?|functional\s+requirements?|non-functional\s+requirements?)\b',
        t
    ):
        return True
    if re.match(
        r'^(?:summarize|summarise)\b.*?\b(?:document|doc|pdf|paper|report|text|article|chapter|section)\b',
        t
    ):
        return True
    if re.search(
        r'\b(?:in|from)\s+the\s+(?:uploaded\s+)?(?:document|doc|pdf|paper|report|thesis)\b|\bon\s+page\s+\d+\b|\b(?:citations?|conclusions?)\b',
        t
    ):
        return True

    if retrieved_documents and re.search(r'\b(?:summarize|summarise|in\s+the\s+file)\b', t):
        return True

    return False


def _build_contextual_rag_query(messages: list) -> str:
    """
    Combines short follow-up queries with the previous user turn so RAG retrieval
    preserves topic context across multi-turn document conversations.
    """
    if not messages:
        return ""
    last_query = str(messages[-1].content).strip()
    if not last_query:
        return ""

    words = last_query.split()
    needs_context = len(words) <= 8 or bool(
        re.search(r'\b(?:it|that|this|those|them|above|more|else|second|first|page|section)\b', last_query.lower())
    )
    if not needs_context or len(messages) < 2:
        return last_query

    prior_humans = [
        str(m.content).strip()
        for m in messages[:-1]
        if isinstance(m, HumanMessage) and str(m.content).strip()
    ]
    if not prior_humans:
        return last_query
    return f"{prior_humans[-1]} — Follow-up: {last_query}"


def _filter_setup_tools(tools: List[dict], query: str) -> List[dict]:
    """Removes workstation launcher tools unless the query is an explicit setup command."""
    if is_workstation_setup_query(query):
        return tools
    return [t for t in tools if t.get("name") not in _SETUP_EXCLUSION_NAMES]


def document_retrieval_node(state: AgentState):
    """
    Post-Route Grounded Context Gathering on the conversational/QA branch:
    Queries the Semantic ETL Pipeline Knowledge Base for relevant passages, requirements,
    and citations from uploaded documents (PDF, DOCX, TXT, MD).
    Stores retrieved context blocks in state['retrieved_documents'].
    """
    messages = state.get("messages", [])
    last_message = messages[-1].content if messages else ""
    if is_conversational_query(last_message):
        return {"retrieved_documents": []}

    try:
        from actions.digital.semantic_etl_client import retrieve_document_context, is_semantic_etl_healthy
        if not is_semantic_etl_healthy():
            return {"retrieved_documents": []}

        rag_query = _build_contextual_rag_query(messages)
        res = retrieve_document_context(rag_query)
        sources = res.get("sources", [])
        if sources:
            print(f"[document_retrieval_node] Injected {len(sources)} grounded document excerpts into state.")
        return {"retrieved_documents": sources}
    except Exception as e:
        print(f"[document_retrieval_node Error]: Context retrieval warning: {e}")
        return {"retrieved_documents": []}


def tool_retrieval_node(state: AgentState):
    """
    RAG LAYER STEP 1: Programmatically query our tool database vector space
    to pull only the top 5 matching candidates.
    """
    if tool_rag_registry.db is None or not any(d.metadata.get("source_type") == "mcp_dormant" for d in tool_rag_registry._tools_source):
        tool_rag_registry.load_dormant_catalog()
        tool_rag_registry.build_index()

    last_message = state["messages"][-1].content
    retrieved_docs = state.get("retrieved_documents", [])
    if is_conversational_query(last_message) or is_document_qa_query(last_message, retrieved_docs):
        return {"active_tools": []}

    # If the user is asking to access external system folders outside MoKa's workspace,
    # bypass tool retrieval so the assistant handles it directly via chat_node without triggering HITL
    from core.routing.layer2.worker_nodes import is_external_system_path_query
    if is_external_system_path_query(last_message):
        return {"active_tools": []}

    # Pull top 5 most matching tools to keep the prompt absolutely razor sharp
    matched_tools = tool_rag_registry.search_relevant_tools(last_message, k=5)

    # 1. Filter out workstation app launchers unless user explicitly issued a setup command
    matched_tools = _filter_setup_tools(matched_tools, last_message)

    # 2. Prune far-off lexical distractors when a much closer semantic match exists
    scored_tools = [t for t in matched_tools if isinstance(t.get("score"), (int, float))]
    if scored_tools and len(matched_tools) == len(scored_tools):
        top_score = scored_tools[0]["score"]
        margin = 0.25 if top_score <= 0.75 else 0.28
        pruned = [t for t in matched_tools if t["score"] <= top_score + margin]
        if pruned:
            matched_tools = pruned

    # 2. If the user is asking for a file operation, guarantee that filesystem tools or dormant pack are present
    if is_file_operation_query(last_message):
        has_fs = any(
            t.get("name") == "mcp_pack_filesystem" or t.get("server_pack_id") == "mcp_pack_filesystem"
            for t in matched_tools
        )
        if not has_fs:
            fs_doc = next(
                (d for d in tool_rag_registry._tools_source if d.metadata.get("tool_name") == "mcp_pack_filesystem" or d.metadata.get("server_pack_id") == "mcp_pack_filesystem"),
                None
            )
            if fs_doc:
                name = fs_doc.metadata["tool_name"]
                matched_tools.insert(0, {
                    "name": name,
                    "description": fs_doc.page_content,
                    "score": 0.5,
                    "source_type": fs_doc.metadata.get("source_type", "mcp_dormant"),
                    "server_pack_id": fs_doc.metadata.get("server_pack_id", "mcp_pack_filesystem"),
                    "input_schema": fs_doc.metadata.get("input_schema", {}),
                    "is_mutating": fs_doc.metadata.get("is_mutating", False)
                })
                matched_tools = matched_tools[:5]

    return {"active_tools": matched_tools}


def summarize_conversation_node(state: AgentState):
    """
    If our conversation gets long, condense older messages into a rolling summary
    and remove them from active short-term memory to keep context windows tiny.
    """
    messages = state["messages"]

    # Only trigger summarization if we have accumulated more than 6 messages
    if len(messages) <= 6:
        return {}

    existing_summary = state.get("summary", "")

    # Format the conversation history as plain text to prevent model confusion
    history_text = ""
    # Keep the last 4 messages (2 full exchanges) in active short-term memory
    messages_to_summarize = messages[:-4]
    for m in messages_to_summarize:
        role = "User" if isinstance(m, HumanMessage) else "Assistant"
        history_text += f"{role}: {m.content}\n"

    summary_prompt = f"""You are a precise conversation summarizer. Your job is to progressively update the summary of a conversation between a User and an Assistant.
    
    Here is the existing summary of the conversation so far:
    "{existing_summary}"
    
    Here are the new lines of conversation that need to be incorporated into the summary:
    {history_text}
    
    Please write a new, concise, updated summary that integrates the new conversation lines into the existing summary. 
    Ensure you preserve key personal details (like the user's name, preferences, or important facts) and key topics discussed.
    Output ONLY the updated summary, with no conversational filler, intros, or outros.
    """

    mode = state.get("provider", "local")
    from core.routing.llm_factory import get_chat_companion_llm
    active_summarizer_llm = get_chat_companion_llm(mode=mode, temperature=0.6)

    response = active_summarizer_llm.invoke([
        SystemMessage(content="You are a precise conversation summarizer that only outputs the summary."),
        HumanMessage(content=summary_prompt)
    ])

    # Create instructions to delete old messages from the Postgres Checkpointer
    delete_messages_instructions = [RemoveMessage(id=m.id) for m in messages_to_summarize]

    return {
        "summary": response.content.strip(),
        "messages": delete_messages_instructions
    }


def memory_retrieval_node(state: AgentState):
    """
    Step 1: Runs a quick similarity check against the permanent database
    using the user's latest input string and the owner ID.
    Directly pulls all facts on broad meta-queries requesting profile summaries.
    """
    last_message = state["messages"][-1].content
    user_id = "cozmo_owner"

    # 1. Identify meta-queries requesting profile summary
    q = last_message.lower()
    meta_triggers = [
        "what do you know about me", 
        "what facts do you know", 
        "tell me all the facts", 
        "tell me facts about me", 
        "what do you remember about me", 
        "tell me about myself",
        "my profile",
        "facts you know"
    ]
    if any(trigger in q for trigger in meta_triggers):
        # Pull all saved facts directly (up to recent 15) to bypass vector limitations on meta-queries
        memories = long_term_memory.get_all_memories(user_id=user_id)
        return {"retrieved_memories": memories[-15:]}

    memories = long_term_memory.retrieve_relevant_memories(last_message, user_id=user_id, limit=3)
    return {"retrieved_memories": memories}


def memory_extraction_node(state: AgentState):
    """
    Step 2: Scans the recent conversation history for permanent profile traits.
    Runs Mem0 asynchronously in a background thread to extract facts, update conflicts,
    and discard ephemeral noise (weather, dates, greetings) without blocking user responses.
    """
    messages = state["messages"]
    if not messages:
        return {}

    # Grab the last 3 messages to preserve dialogue context.
    # When grounded document excerpts were used on this turn, omit assistant turns so
    # technical document content does not leak into long-term biographical user memory.
    recent_messages = messages[-3:]
    has_doc_context = bool(state.get("retrieved_documents"))
    dialogue_turns = []
    for m in recent_messages:
        is_human = isinstance(m, HumanMessage)
        if has_doc_context and not is_human:
            continue
        role = "user" if is_human else "assistant"
        dialogue_turns.append({"role": role, "content": m.content})

    if not dialogue_turns:
        return {}

    user_id = "cozmo_owner"

    @traceable(name="Mem0 Long-Term Memory Extraction", run_type="chain")
    def run_extraction_bg():
        try:
            long_term_memory.add_dialogue(dialogue_turns, user_id=user_id)
            sys.stdout.flush()
        except Exception as e:
            print(f"\n{GRAY} [LONG-TERM MEMORY ERROR]: Failed background extraction: {e}{RESET}\n: ", end="")
            sys.stdout.flush()

    threading.Thread(target=run_extraction_bg, daemon=False).start()
    return {}


def route_query(state: AgentState):
    last_message = state["messages"][-1].content
    active_tools = state.get("active_tools", [])
    retrieved_docs = state.get("retrieved_documents", [])

    # Fast-path for conversational greetings, explicit document Q&A, or when no tools passed the RAG gate
    if is_conversational_query(last_message) or is_document_qa_query(last_message, retrieved_docs) or not active_tools:
        return {"next_route": "none"}

    # Strict rule: Filter out workstation setups if query is not an explicit setup command
    active_tools = _filter_setup_tools(active_tools, last_message)

    # Strict rule: If user query is a file operation request, remove setup_coding from options
    if is_file_operation_query(last_message):
        active_tools = [t for t in active_tools if t.get("name") != "setup_coding"]
        if not active_tools:
            return {"next_route": "mcp_pack_filesystem"}

    if not active_tools:
        return {"next_route": "none"}

    # Formulate typed choice criteria dictionary from Top-K RAG selection.
    # Dynamically derive readable semantic labels for MCP tools from catalog display_name metadata
    # (avoiding opaque mcp_pack_* / vendor-prefixed keys in LAYA), then map back to exact tool names.
    catalog = {}
    try:
        from core.routing.layer2.mcp_manager import mcp_manager
        catalog = mcp_manager.get_catalog()
    except Exception:
        catalog = {}

    def _slugify(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

    laya_to_tool_name = {}
    tools_dict = {}
    for tool in active_tools:
        t_name = tool["name"]
        laya_key = t_name
        source_type = tool.get("source_type")
        pack_id = tool.get("server_pack_id") or (t_name if source_type == "mcp_dormant" else None)
        display_name = catalog.get(pack_id, {}).get("display_name") if pack_id else None
        if display_name:
            dn_slug = _slugify(display_name)
            if dn_slug:
                if source_type == "mcp_dormant":
                    laya_key = dn_slug
                elif source_type == "mcp_active":
                    laya_key = f"{dn_slug}_{t_name}"
        while laya_key in tools_dict:
            laya_key = f"{laya_key}_"
        tools_dict[laya_key] = tool["description"]
        laya_to_tool_name[laya_key] = t_name
    tools_dict["none"] = (
        "Core conversational and Document QA channel. Select for casual chat, greetings, personal facts, "
        "general discussion, or answering questions, summarizing, and explaining uploaded documents or specifications."
    )
    instructions = (
        "Select the appropriate tool or action to execute given the user's input/state. "
        "If the user input is casual chat, greetings, personal facts, jokes, or a question/summary "
        "about uploaded documents or general knowledge rather than executing an external tool, select 'none'."
    )

    questions = {
        "tool_selection": {
            "type": "choice",
            "instructions": instructions,
            "criteria": tools_dict,
        }
    }

    try:
        agent = get_laya_agent()
        result = agent.predict(last_message, questions)
        answers = result.get("answers", result)
        decision = answers.get("tool_selection", {})
        raw_choice = decision.get("choice", "none")
        selected_route = laya_to_tool_name.get(raw_choice, raw_choice)
    except Exception as e:
        print(f"[route_query Error] Laya prediction failed: {e}. Falling back to 'none'.")
        selected_route = "none"

    # Strict Guard 1: If setup_coding was selected despite a file operation intent, redirect to filesystem
    if selected_route == "setup_coding" and is_file_operation_query(last_message):
        print(f"[route_query Guard] Blocked setup_coding for file operation query: '{last_message}'. Redirecting to filesystem.")
        fs_tool = next(
            (t["name"] for t in active_tools if t.get("name") != "setup_coding" and ("file" in t["name"] or t.get("server_pack_id") == "mcp_pack_filesystem")),
            "mcp_pack_filesystem"
        )
        selected_route = fs_tool
    # Guard 2: Workstation launchers should NEVER trigger on non-setup queries
    elif selected_route in _SETUP_EXCLUSION_NAMES and not is_workstation_setup_query(last_message):
        print(f"[route_query Guard] Blocked {selected_route} for non-setup query: '{last_message}'. Routing to conversational chat_node.")
        selected_route = "none"

    return {"next_route": selected_route}


def decide_next_step(state: AgentState) -> str:
    """Evaluates router output and targets a node execution branch."""
    route = state.get("next_route", "none")
    if route == "none":
        return "document_retrieval_node"

    # Check if route is an uninstalled/dormant MCP pack stub
    active_tools = state.get("active_tools", [])
    tool_meta = next((t for t in active_tools if t.get("name") == route), None)
    if tool_meta and tool_meta.get("source_type") == "mcp_dormant":
        return "mcp_discovery_node"

    # Native tools or dynamically ingested mcp_active tools
    return "execute_tool_node"


def mcp_discovery_node(state: AgentState):
    """
    Gate 1 HITL checkpoint:
    Pauses execution and asks the user whether they want MoKa to add the new tool/MCP pack.
    """
    from langgraph.types import interrupt
    from core.routing.layer2.mcp_manager import mcp_manager

    pack_id = state.get("next_route", "")
    catalog = mcp_manager.get_catalog()
    server_cfg = catalog.get(pack_id, {})
    display_name = server_cfg.get("display_name", pack_id)
    description = server_cfg.get("description", "")

    # Request human confirmation to add the tool
    decision = interrupt({
        "type": "hitl_interrupt",
        "interrupt_type": "mcp_discovery",
        "server_pack_id": pack_id,
        "display_name": display_name,
        "description": description,
        "message": f"I need the '{display_name}' tool to help you with that. Would you like me to add it so I can use it?"
    })

    approved = False
    if isinstance(decision, dict):
        approved = bool(decision.get("approved"))
    elif isinstance(decision, bool):
        approved = decision
    elif isinstance(decision, str):
        approved = decision.strip().lower() in ("yes", "y", "true", "approve", "1")

    if approved:
        print(f"[mcp_discovery_node] User APPROVED adding '{display_name}'. Connecting & ingesting tools...")
        try:
            connect_res = mcp_manager.connect_server_sync(pack_id)
            tools_count = connect_res.get("tools_count", 0)
            print(f"[mcp_discovery_node] Successfully added {tools_count} tools from '{display_name}'.")
            return {
                "resumed_from_interrupt": True,
                "mcp_active_servers": mcp_manager.get_active_pack_ids(),
                "next_route": "re_evaluate"
            }
        except Exception as e:
            print(f"[mcp_discovery_node Error] Failed to connect '{pack_id}': {e}")
            return {
                "resumed_from_interrupt": True,
                "messages": [AIMessage(content=f"I tried to add '{display_name}', but encountered an issue: {e}")],
                "next_route": "none"
            }
    else:
        print(f"[mcp_discovery_node] User DECLINED adding '{display_name}'.")
        return {
            "resumed_from_interrupt": True,
            "messages": [AIMessage(content=f"Understood! I won't add '{display_name}'. Let me know if you need help with anything else.")],
            "next_route": "none"
        }


def decide_discovery_step(state: AgentState) -> str:
    """Evaluates whether to loop back to tool_retrieval_node after MCP addition or finish."""
    route = state.get("next_route", "none")
    if route == "re_evaluate":
        return "tool_retrieval_node"
    return "summarize_conversation_node"

