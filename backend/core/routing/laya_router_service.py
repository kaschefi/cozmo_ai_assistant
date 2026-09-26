import os
from typing import Dict, List, Optional
from fastapi import FastAPI
from pydantic import BaseModel
import laya

# Prevent TensorFlow import race conditions if installed alongside transformers
os.environ["USE_TF"] = "0"

app = FastAPI(title="Moka LAYA Decision Router")

# Preload the resident model checkpoint
MODEL_ID = "convaiinnovations/laya-typed-decisions"
print(f"Loading {MODEL_ID} into memory...")
agent = laya.load(MODEL_ID)


class RouteRequest(BaseModel):
    state: str
    tools: Dict[str, str]  # tool_name: description/criteria


class RouteResponse(BaseModel):
    selected_tool: str
    confidence: float
    probabilities: Dict[str, float]


@app.post("/route", response_model=RouteResponse)
def route_intent(req: RouteRequest):
    # Formulate a typed 'choice' question over tool options
    questions = {
        "tool_selection": {
            "type": "choice",
            "instructions": "Select the appropriate tool or action to execute given the state/input.",
            "criteria": req.tools,
        }
    }

    # Predict in a single forward pass (~33ms)
    result = agent.predict(req.state, questions)
    decision = result["tool_selection"]

    return RouteResponse(
        selected_tool=decision["choice"],
        confidence=decision.get("confidence", 0.0),
        probabilities=decision.get("probabilities", {}),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8088)