import os
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from core.routing.llm_factory import get_llm
from core.routing.tool_vector_db import tool_rag_registry

load_dotenv()

qwen25 = get_llm("WEATHER_LLM_MODEL", "qwen2.5:3b", temperature=0)


tool_rag_registry.register_tool_schema(
    name="weather_node",
    description="Provides real-time weather updates, climate forecasts, temperature, precipitation, rain, snow, or wind details."
)
def get_weather_prompt(state) -> list:
    current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

    return [SystemMessage(content=f"""You are Cozmo's specialized Weather Agent.
Your ONLY job is to provide accurate weather updates by using your tools.

CURRENT REAL-WORLD CONTEXT:
- Today's Date and Time: {current_time}
- Default Location: Vienna

STRICT DEFAULT RULES:
If the user's request is missing specific details, you MUST apply these defaults before using your tool:
1. City: If no city is specified, use the default location.
2. Date/Time: Use the Current Real-World Context to figure out what "today", "tomorrow", or "right now" means.

INSTRUCTIONS:
1. Extract the location.
2. ALWAYS use the `get_weather` tool to fetch the data. NEVER guess or hallucinate the weather.
3. Read the raw data returned by the tool.
4. Respond with a short, natural, conversational sentence that Cozmo can speak out loud. You MUST always explicitly include the exact temperature (in degrees) in your sentence. Never summarize it as just 'sunny' or 'rainy' without mentioning the exact temperature.

Example Output: "Right now in Vienna, it's 14 degrees and partly cloudy."
""")]


# 2. Weather Tool
@tool
def get_weather(city: str) -> str:
    """Fetches the current weather for a specific city."""
    import requests
    # Normalize city
    c = city.strip().lower()
    
    # 1. Try public wttr.in service first but with a generous 15-second timeout
    try:
        response = requests.get(f'https://wttr.in/{city}?format=3', timeout=15)
        response.raise_for_status()
        raw = response.text
        # Sanitize: remove characters that Windows cp1252 console can't display (e.g. weather emoji)
        sanitized = raw.encode('ascii', errors='ignore').decode('ascii').strip()
        return sanitized if sanitized else raw.encode('cp1252', errors='replace').decode('cp1252').strip()
    except Exception as e:
        print(f"[get_weather] wttr.in failed or timed out: {e}. Trying fallback Open-Meteo API...")
        
        # 2. High-speed fallback for Vienna specifically (default city)
        if "vienna" in c or not c:
            try:
                # Open-Meteo is open-source, keyless, and resolves in <100ms
                fallback_url = "https://api.open-meteo.com/v1/forecast?latitude=48.2085&longitude=16.3725&current=temperature_2m,weather_code"
                res = requests.get(fallback_url, timeout=5)
                res.raise_for_status()
                data = res.json()
                
                temp_val = data.get("current", {}).get("temperature_2m", "12")
                temp = f"+{temp_val}" if float(temp_val) >= 0 else str(temp_val)
                
                # Decode weather code
                code = data.get("current", {}).get("weather_code", 0)
                cond = "Clear"
                if code in [1, 2, 3]: cond = "Partly Cloudy"
                elif code in [45, 48]: cond = "Foggy"
                elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]: cond = "Rainy"
                elif code in [71, 73, 75, 77, 85, 86]: cond = "Snowy"
                elif code in [95, 96, 99]: cond = "Stormy"
                
                return f"Vienna: {cond} {temp}C"
            except Exception as fallback_err:
                print(f"[get_weather] Fallback API failed as well: {fallback_err}")
                return f"Weather service completely unavailable. Connection issue: {fallback_err}"
        
        return f"Weather service unavailable for '{city}': {e}"


weather_worker = create_react_agent(
    model=qwen25,
    tools=[get_weather],
    prompt=get_weather_prompt
)