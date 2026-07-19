from core.routing.tool_vector_db import tool_rag_registry
import subprocess
import sys
import os
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from langchain_core.messages import ToolMessage
from core.routing.llm_factory import get_llm

# 1. Define the Sandbox directly as a LangChain Tool using the @tool decorator
@tool
def execute_python_sandbox(code_string: str) -> str:
    """
    Executes a raw Python code string inside an isolated local subprocess
    and captures stdout print statements or stderr exceptions.
    Use this tool whenever you need exact calculations, algorithmic logic, 
    list transformations, or text parsing that requires absolute accuracy.
    Always use print() inside the script to capture the final output.
    """
    # Clean up any potential markdown structural artifacts
    if "```python" in code_string:
        code_string = code_string.split("```python")[1].split("```")[0]
    elif "```" in code_string:
        code_string = code_string.split("```")[1].split("```")[0]

    temp_file = "moka_isolated_sandbox.py"

    # Note: Using your direct file manipulation pattern safely
    f = open(temp_file, "w", encoding="utf-8")
    f.write(code_string.strip())
    f.close()

    try:
        result = subprocess.run(
            [sys.executable, temp_file],
            capture_output=True,
            text=True,
            timeout=8
        )
        if result.returncode == 0:
            return result.stdout if result.stdout.strip() else "Success: Code executed, but nothing was printed."
        return f"Execution Error:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Code timed out after 8 seconds."
    except Exception as e:
        return f"Pipeline Error: {str(e)}"
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def code_executor(input_string: str) -> str :
    prompt = """You are an expert computational reasoning agent.

Your primary responsibility is to solve problems that require exact computation, deterministic logic, structured data processing, or simulation.

You have access to a Python execution tool that runs code inside an isolated sandbox. Whenever accuracy matters, you MUST use the Python tool instead of reasoning mentally.

Core Principle:
Tool first, answer second.

For any task requiring deterministic computation or verification, execute Python first. Treat the tool's output as the authoritative source of truth. Do not derive the final answer from mental reasoning when the tool can compute or verify it.

Always prefer Python for tasks involving:

• Arithmetic, algebra, percentages, ratios, statistics, or financial calculations
• Unit conversions or dimensional analysis
• Multi-step numerical computations
• Counting, aggregation, or combinatorics
• Matrix or vector operations
• Date/time calculations
• Parsing, filtering, sorting, or transforming structured or semi-structured data
• JSON, CSV, dictionaries, nested lists, or tabular manipulation
• String processing requiring deterministic behavior
• Validation against rules or constraints
• Simulations or state updates
• Algorithmic logic
• Verification of another model's calculations
• Any computation where an incorrect answer would be unacceptable

Do NOT rely on mental arithmetic for these tasks.

When using Python:

1. Write complete, executable Python code.
2. Use print() to output the final answer.
3. Keep the script minimal and deterministic.
4. Do not request user interaction.
5. Do not read or write files unless explicitly asked.
6. Do not access the network.
7. Handle edge cases whenever practical.
8. If parsing user data, preserve correctness over elegance.
9. If execution fails due to a coding mistake, fix the code and retry once before responding.

If the task does NOT require computation or deterministic processing, answer directly without using Python.

After receiving the Python output:
- Treat the execution result as the ground truth.
- Interpret the result.
- Present a concise, human-readable answer.
- Do not expose unnecessary implementation details unless requested.
- If execution ultimately fails, explain why and include the final execution error.

Your objective is correctness first, reliability second, efficiency third, brevity fourth.

Never guess when exact computation is possible.
When computation can determine the answer, always execute first and answer from the execution result.
Persona and Voice Guidelines:
• Identity: You are Moka, a supportive, intelligent, and grounded AI companion. 
• Tone: Maintain an authentic, natural, and slightly warm tone. Speak like an expert teammate or an insightful peer, not an automated terminal.
• Response Delivery: When translating the raw sandbox data into a final message for the user, wrap the facts in natural conversational prose. Never just spit out a bare number or a single equation unless explicitly asked. Give the answer with a touch of personality.

Example Transformations:
- Raw data: "4" 
  Instead of writing "**4**", say: "That would be 4! What's next on the list?"
"""
    llm = ChatOllama(
        model="ornith:9b",
        temperature=0.1,
        base_url="http://localhost:11434"
    )

    tools_list = [execute_python_sandbox]
    tools_dict = {tool.name: tool for tool in tools_list}

    llm_with_tools = llm.bind_tools(tools_list)

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=input_string)
    ]

    #Let Ornith decide if it wants to use the sandbox
    response = llm_with_tools.invoke(messages)
    messages.append(response)

    if response.tool_calls:
        for tool_call in response.tool_calls:
            selected_tool = tools_dict[tool_call["name"]]
            tool_output = selected_tool.invoke(tool_call["args"])

            # Append the sandbox result back to the chat history
            messages.append(ToolMessage(content=str(tool_output), tool_call_id=tool_call["id"]))

        final_response = llm_with_tools.invoke(messages)
        return final_response.content
    return response.content

# registering the tool with RAG for Multimodal functionality

#  Arithmetic & Calculation Dimension
tool_rag_registry.register_tool_schema(
    name="code_executor_node",
    description="Mathematical calculations, algebra, fractions, percentages, averages, exact arithmetic, and geometry radius computations."
)

#  Logic, Rules, & Algorithms Dimension
tool_rag_registry.register_tool_schema(
    name="code_executor_node",
    description="Computational logic puzzles, coordinate navigation movement, rule checks, password validation, parenthetical balancing, and condition checking."
)

#  List & Array Data Processing Dimension
tool_rag_registry.register_tool_schema(
    name="code_executor_node",
    description="Manipulating data lists, sorting values, filtering duplicates, counting occurrences, array operations, and structured JSON/CSV formatting."
)

#  String Parsing & Conversions Dimension
tool_rag_registry.register_tool_schema(
    name="code_executor_node",
    description="Parsing strings, extracting numbers from text, unit conversions, date subtraction, days between dates, and substring formatting."
)


if __name__ == "__main__":
    print(code_executor("can you please tell me what is the square root of 25"))