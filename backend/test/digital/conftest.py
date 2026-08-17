import os
from dotenv import load_dotenv

# Run initialization prior to any execution threads running inside the folder
load_dotenv()

# Strict environment target guarantees your test traces are filed correctly
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "moka-assistant-testing"