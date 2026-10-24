# backend/test/digital/routers/tools/cognitive.py
"""
Namespace: cognitive.*
Cognitive sub-agents: Web Search, Google Calendar, Weather, Code Executor Sandbox, Todoist Tasks,
Gmail, Maps & Directions, Language Translation, Text Summarization, and Personal Contacts.
"""

from typing import Dict, List

COGNITIVE_NAMESPACE = "cognitive"

# -----------------------------------------------------------------------------
# Multiple Short Explanations (Dimensions) for code_executor_node
# Mirroring backend/actions/digital/langchain/code_executor.py:L152-L182.
# In Layer 1 (FastEmbed / FAISS Tool RAG), each dimension is indexed as an
# independent vector document to prevent vector dilution and score high similarity.
# -----------------------------------------------------------------------------
CODE_EXECUTOR_DIMENSIONS: Dict[str, str] = {
    # Dimension 1: Arithmetic & Calculation
    "arithmetic_calculation": (
        "Mathematical calculations, arithmetic computations, calculating square root of numbers, "
        "multiplication, division, algebra, fractions, percentages, averages, exact arithmetic, and geometry radius computations."
    ),
    # Dimension 2: Logic, Rules, & Algorithms
    "logic_algorithms": (
        "Computational logic puzzles, coordinate navigation movement, rule checks, "
        "password validation, parenthetical balancing, and condition checking."
    ),
    # Dimension 3: List & Array Data Processing
    "list_array_processing": (
        "Manipulating data lists, sorting values, filtering duplicates, counting occurrences, "
        "array operations, and structured JSON/CSV formatting."
    ),
    # Dimension 4: String Parsing & Conversions
    "string_parsing_conversions": (
        "Parsing strings, extracting numbers from text, unit conversions, "
        "date subtraction, days between dates, and substring formatting."
    ),
    # Dimension 5: String & Character Reversal
    "string_character_reversal": (
        "String reversal, spelling words backwards, reversing text or characters, "
        "word manipulation, character inversion, and word flipping."
    ),
}

# -----------------------------------------------------------------------------
# Core Cognitive Tools (Active in baseline MoKa)
# -----------------------------------------------------------------------------
COGNITIVE_BASE_TOOLS: Dict[str, str] = {
    "calendar_node": (
        "Manages Google Calendar operations, schedules, and appointments. "
        "Use when user wants to view, check, create, schedule, sync, reschedule, move, change, or delete meetings, "
        "appointments, team standups, calendar events, or check agenda."
    ),
    "weather_node": (
        "Provides real-time weather conditions, forecasts, and temperatures (Celsius) for any specified city. "
        "Use for rain, temperature, outside conditions, or weather forecasts."
    ),
    "web_search_node": (
        "Searches the live web to find online information, breaking news headlines, space exploration, "
        "sports match winners and scores, company financial market cap, or answering general factual questions."
    ),
    "code_executor_node": (
        "Executes Python code in an isolated sandbox for exact deterministic computation across 5 dimensions: "
        "(1) Math calculations, arithmetic, and square roots; "
        "(2) Computational logic puzzles and rule verification; "
        "(3) List and array operations, sorting, and duplicate filtering; "
        "(4) String parsing, unit conversions, and date subtraction; "
        "(5) Word and character reversal or spelling backwards."
    ),
    "todolist_node": (
        "Manages Todoist tasks, to-do lists, and personal checklists. "
        "Use when user wants to add, create, or schedule a task, check off, mark done, finish or complete a task, "
        "delete or remove a task, list active or pending tasks, view items left on checklist, or organize project to-dos."
    ),
}

# -----------------------------------------------------------------------------
# Extended Cognitive Tools (Scaling to 100 tools)
# -----------------------------------------------------------------------------
COGNITIVE_EXTRA_TOOLS: Dict[str, str] = {
    "gmail_node": (
        "Manages Gmail email operations. "
        "Use when user wants to read, check, search, summarize, draft, send, or reply to emails and inbox messages."
    ),
    "maps_directions_node": (
        "Provides driving, walking, and transit directions, travel time, and distance between locations. "
        "Use when user asks how to get somewhere, how long a trip takes, or route to an address."
    ),
    "translation_node": (
        "Translates words, sentences, and phrases between languages. "
        "Use when user asks how to say something in another language, translate this text, or what a foreign phrase means."
    ),
    "summarizer_node": (
        "Summarizes long text, articles, web page URLs, and documents into short key points. "
        "Use when user asks to summarize, shorten, give the gist, TL;DR, or extract key points from content."
    ),
    "contacts_node": (
        "Looks up saved contacts, phone numbers, email addresses, and birthdays of people. "
        "Use when user asks for someone's number, email address, or contact details."
    ),
}

# Unified 10 cognitive tools dictionary
COGNITIVE_TOOLS: Dict[str, str] = {
    **COGNITIVE_BASE_TOOLS,
    **COGNITIVE_EXTRA_TOOLS,
}

# Layer 1 Tool RAG specifications for cognitive tools (including 5 separate documents for code_executor_node)
COGNITIVE_RAG_SPECS: List[Dict[str, str]] = [
    {"name": "calendar_node", "description": COGNITIVE_TOOLS["calendar_node"], "namespace": COGNITIVE_NAMESPACE},
    {"name": "weather_node", "description": COGNITIVE_TOOLS["weather_node"], "namespace": COGNITIVE_NAMESPACE},
    {"name": "web_search_node", "description": COGNITIVE_TOOLS["web_search_node"], "namespace": COGNITIVE_NAMESPACE},
    {"name": "todolist_node", "description": COGNITIVE_TOOLS["todolist_node"], "namespace": COGNITIVE_NAMESPACE},
    # 5 discrete short dimensions for code_executor_node
    {"name": "code_executor_node", "description": CODE_EXECUTOR_DIMENSIONS["arithmetic_calculation"], "namespace": COGNITIVE_NAMESPACE},
    {"name": "code_executor_node", "description": CODE_EXECUTOR_DIMENSIONS["logic_algorithms"], "namespace": COGNITIVE_NAMESPACE},
    {"name": "code_executor_node", "description": CODE_EXECUTOR_DIMENSIONS["list_array_processing"], "namespace": COGNITIVE_NAMESPACE},
    {"name": "code_executor_node", "description": CODE_EXECUTOR_DIMENSIONS["string_parsing_conversions"], "namespace": COGNITIVE_NAMESPACE},
    {"name": "code_executor_node", "description": CODE_EXECUTOR_DIMENSIONS["string_character_reversal"], "namespace": COGNITIVE_NAMESPACE},
    # 5 extended cognitive tools
    {"name": "gmail_node", "description": COGNITIVE_TOOLS["gmail_node"], "namespace": COGNITIVE_NAMESPACE},
    {"name": "maps_directions_node", "description": COGNITIVE_TOOLS["maps_directions_node"], "namespace": COGNITIVE_NAMESPACE},
    {"name": "translation_node", "description": COGNITIVE_TOOLS["translation_node"], "namespace": COGNITIVE_NAMESPACE},
    {"name": "summarizer_node", "description": COGNITIVE_TOOLS["summarizer_node"], "namespace": COGNITIVE_NAMESPACE},
    {"name": "contacts_node", "description": COGNITIVE_TOOLS["contacts_node"], "namespace": COGNITIVE_NAMESPACE},
]

# Backward-compatibility alias
COGNITIVE_EXTRA_RAG_SPECS: List[Dict[str, str]] = [
    {"name": name, "description": desc, "namespace": COGNITIVE_NAMESPACE}
    for name, desc in COGNITIVE_EXTRA_TOOLS.items()
]
