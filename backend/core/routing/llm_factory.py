import os
from dotenv import load_dotenv

load_dotenv()


def get_llm(model_env_var: str, default_model: str, temperature: float = 0.0):
    """
    Creates and returns the appropriate Chat Model based on LLM_PROVIDER.
    Supports LLM_PROVIDER=OLLAMA (default) and LLM_PROVIDER=AZURE.
    """
    provider = os.getenv("LLM_PROVIDER", "OLLAMA").upper().strip()

    if provider == "AZURE":
        # Import dynamically so that the langchain-openai dependency is only loaded when needed
        from langchain_openai import AzureChatOpenAI

        # Check for model-specific deployment override, fallback to general chat deployment name
        dep_suffix = model_env_var.replace("_LLM_MODEL", "").replace("_MODEL", "")
        dep_var_name = f"AZURE_{dep_suffix}_DEPLOYMENT"
        deployment_name = os.getenv(dep_var_name) or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")

        if not all([deployment_name, endpoint, api_key]):
            # Give a very clear explanation of what keys are missing if it fails
            missing = []
            if not deployment_name:
                missing.append(f"{dep_var_name} or AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
            if not endpoint:
                missing.append("AZURE_OPENAI_ENDPOINT")
            if not api_key:
                missing.append("AZURE_OPENAI_API_KEY")
            raise ValueError(
                f"LLM_PROVIDER is set to AZURE, but configuration variables are missing: {', '.join(missing)}."
            )

        return AzureChatOpenAI(
            azure_deployment=deployment_name,
            openai_api_version=api_version,
            azure_endpoint=endpoint,
            api_key=api_key,
            temperature=temperature
        )

    else:
        # Default fallback is OLLAMA
        from langchain_ollama import ChatOllama

        model = os.getenv(model_env_var, default_model)
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        return ChatOllama(
            model=model,
            temperature=temperature,
            base_url=base_url
        )
