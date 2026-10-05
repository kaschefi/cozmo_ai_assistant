import os
from dotenv import load_dotenv

load_dotenv()


_MODEL_CACHE = {}

def get_llm(model_env_var: str, default_model: str, temperature: float = 0.0, provider: str = None):
    """
    Creates and returns the appropriate Chat Model based on LLM_PROVIDER or explicit provider override.
    Supports provider="OLLAMA" / "LOCAL" and provider="AZURE" / "CLOUD".
    """
    selected_provider = (provider or os.getenv("LLM_PROVIDER", "OLLAMA")).upper().strip()
    if selected_provider in ["CLOUD", "AZURE"]:
        resolved_provider = "AZURE"
    else:
        resolved_provider = "OLLAMA"

    cache_key = (model_env_var, default_model, temperature, resolved_provider)
    if cache_key in _MODEL_CACHE:
        return _MODEL_CACHE[cache_key]

    if resolved_provider == "AZURE":
        dep_suffix = model_env_var.replace("_LLM_MODEL", "").replace("_MODEL", "")
        dep_var_name = f"AZURE_{dep_suffix}_DEPLOYMENT"
        
        deployment_name = (
            os.getenv(dep_var_name)
            or os.getenv("AZURE_MODEL_NAME")
            or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
        )
        if not deployment_name:
            raw_nano = os.getenv("AZURE_GPT_4.1_NANO", "")
            if raw_nano and "azureml://" not in raw_nano:
                deployment_name = raw_nano
            else:
                deployment_name = "Phi-4-mini-instruct"

        endpoint = (
            os.getenv("AZURE_SERVICES_ENDPOINT")
            or os.getenv("AZURE_OPENAI_ENDPOINT")
            or "https://moka101.services.ai.azure.com/openai/v1"
        )
        api_key = os.getenv("AZURE_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

        if not all([deployment_name, endpoint, api_key]):
            missing = []
            if not deployment_name:
                missing.append("AZURE_MODEL_NAME or deployment_name")
            if not endpoint:
                missing.append("AZURE_OPENAI_ENDPOINT or AZURE_SERVICES_ENDPOINT")
            if not api_key:
                missing.append("AZURE_API_KEY or AZURE_OPENAI_API_KEY")
            raise ValueError(
                f"LLM_PROVIDER is set to AZURE/CLOUD, but configuration variables are missing: {', '.join(missing)}."
            )

        if "services.ai.azure.com" in endpoint or "/openai/v1" in endpoint:
            from langchain_openai import ChatOpenAI
            base_url = endpoint.rstrip("/") + "/"
            client = ChatOpenAI(
                base_url=base_url,
                model=deployment_name,
                api_key=api_key,
                temperature=temperature
            )
        else:
            from langchain_openai import AzureChatOpenAI
            clean_endpoint = endpoint.replace("/openai/v1", "").rstrip("/")
            client = AzureChatOpenAI(
                azure_deployment=deployment_name,
                openai_api_version=api_version,
                azure_endpoint=clean_endpoint,
                api_key=api_key,
                temperature=temperature
            )

        _MODEL_CACHE[cache_key] = client
        return client

    else:
        # Default fallback is OLLAMA (LOCAL)
        from langchain_ollama import ChatOllama

        model = os.getenv(model_env_var, default_model)
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        client = ChatOllama(
            model=model,
            temperature=temperature,
            base_url=base_url
        )
        _MODEL_CACHE[cache_key] = client
        return client


def get_chat_companion_llm(mode: str = "local", temperature: float = 0.6):
    """Returns chat companion / summarizer LLM (Ollama in local mode, Azure Phi-4-mini in cloud mode)."""
    prov = "AZURE" if str(mode).lower() == "cloud" else "OLLAMA"
    return get_llm("CHAT_LLM_MODEL", "qwen2.5:3b", temperature=temperature, provider=prov)


def get_calendar_llm(mode: str = "local", temperature: float = 0.0):
    """Returns Google Calendar sub-agent LLM (Ollama qwen3.5:4b in local, Azure Phi-4-mini in cloud)."""
    prov = "AZURE" if str(mode).lower() == "cloud" else "OLLAMA"
    return get_llm("CALENDAR_LLM_MODEL", "qwen3.5:4b", temperature=temperature, provider=prov)


def get_todolist_llm(mode: str = "local", temperature: float = 0.0):
    """Returns Todoist sub-agent LLM (Ollama qwen3.5:4b in local, Azure Phi-4-mini in cloud)."""
    prov = "AZURE" if str(mode).lower() == "cloud" else "OLLAMA"
    return get_llm("TODOLIST_LLM_MODEL", "qwen3.5:4b", temperature=temperature, provider=prov)


def get_groq_model(model_name="Compound", temperature=0.7):
    from langchain_groq import ChatGroq
    return ChatGroq(
        temperature=temperature,
        groq_api_key=os.getenv("GROQ_API_KEY"),
        model_name=model_name
    )

