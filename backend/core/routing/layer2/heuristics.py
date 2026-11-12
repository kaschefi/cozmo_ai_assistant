# core/routing/layer2/heuristics.py
import re
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage
from core.routing.layer2.config import DEFAULT_CONFIG


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


def filter_setup_tools(tools: List[Dict[str, Any]], query: str, exclusion_names=DEFAULT_CONFIG.setup_exclusion_names) -> List[Dict[str, Any]]:
    """Removes workstation launcher tools unless the query is an explicit setup command."""
    if is_workstation_setup_query(query):
        return tools
    return [t for t in tools if t.get("name") not in exclusion_names]


def build_contextual_rag_query(messages: list) -> str:
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


def is_document_inquiry_query(text: str) -> bool:
    """
    Detects whether user query is an explicit inquiry about uploaded documents,
    PDFs, specifications, papers, or thesis materials in the knowledge base.
    """
    if not text:
        return False
    t = text.strip().lower()
    doc_patterns = [
        r'\b(?:uploaded|indexed|knowledge\s+base|document|documents|doc|docs|pdf|docx|paper|thesis|srs|specification|specifications|specs|citation|citations)\b',
        r'\b(?:in|from|according\s+to|what\s+does)\s+(?:the\s+)?(?:document|doc|pdf|paper|thesis|specs?|file)\b',
        r'\b(?:page|section|chapter|appendix|table|figure)\s+\d+\b',
    ]
    return any(re.search(p, t) for p in doc_patterns)


