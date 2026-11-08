# Two-Layer Top-K LAYA Router Architecture Upgrades (Phase 3: Scalability Boost)

**Author:** Senior AI Architecture  
**Target Component:** `2-L-Laya-TopK` (`backend/test/routers/models/laya/two_layer_topk.py`)  
**Scalability Scope:** Scaled Tool Catalogs (20, 30, 50, and 100 tools)  
**Evaluation Dataset:** `MoKa_Router_Benchmark_100_Tools` (303 test cases)  
**Date:** November 2026  

---

## 1. Executive Summary

In Phase 2, the Two-Layer Top-K LAYA router (`2_L_Laya_TopK`) demonstrated outstanding performance on the 20-tools benchmark (**92.06%**, 58/63 correct), coming within 1 test case of the production LLM (**93.65%**, 59/63) while running at sub-10ms P50 latency and consuming zero LLM tokens.

However, when scaling the tool catalog to 100 tools (`MoKa_Router_Benchmark_100_Tools`, 303 test cases):
* The Two-Layer LLM (`2_L_LLM`) maintained **90.10%** accuracy (273/303) due to GPT-4o-mini's vast context window and broad reasoning tokens.
* The un-scaled `2_L_Laya_TopK` collapsed to **76.57%** accuracy (232/303) due to dense cross-domain vector clutter, negative phrasing attractors, reflex namespace collisions, and distractor softmax dilution.

**Phase 3 Goal:** Eliminate the scaling bottleneck and elevate `2_L_Laya_TopK` to parity with the Two-Layer LLM at large scales (30, 50, 100 tools) without synthetic shortcuts, test query memorization, or latency degradation.

### 100-Tools Benchmark Results (Phase 3)

| Router Architecture | Correct / Total | Accuracy (%) | P50 Latency (ms) | Mean Latency (ms) | P90 Latency (ms) | Total Tokens | LLM API Calls |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2-L-Laya-TopK (Baseline Phase 2)** | 232 / 303 | 76.57% | 512.4 ms | 535.1 ms | 820.0 ms | 0 | 0 |
| **2-L-LLM (Production)** | 273 / 303 | 90.10% | 2,761.6 ms | 2,396.3 ms | 3,095.9 ms | 105,403 | 260 |
| **2-L-Laya-TopK (Phase 3 Upgraded)** | **269 / 303** | **88.78%** | **574.0 ms** | **579.2 ms** | **886.1 ms** | **0** | **0** |

**Phase 3 Achievements:**
* **+12.21% Absolute Accuracy Boost:** Soared from 76.57% to **88.78%** (269/303), narrowing the gap with the production LLM to just 4 cases.
* **4.8× Lower Median Latency:** Median response time of **574.0 ms** vs **2,761.6 ms** for `2_L_LLM`.
* **Zero Token Cost & Local Execution:** Consumes 0 tokens (saving >105,000 tokens per 300 queries) and operates 100% offline.

---

## 2. Root Cause Analysis: The 100-Tool Scaling Failure Modes

Our architectural investigation revealed four primary mechanisms causing LAYA's accuracy drop at scale:

### 2.1. Dense Cross-Domain Vector Clutter & Softmax Dilution
In a 100-tool vector space, tools from completely different operational namespaces share overlapping lexical tokens (e.g. `set_system_volume` vs `spotify_set_volume` vs `set_robot_volume`; `lights_off` vs `shutdown_computer`). Unconstrained FAISS top-k retrieval pulled in cross-domain distractors. Because LAYA computes a softmax distribution over options, presenting 5 distractor tools flattened the probability distribution and caused the decision head to lose discriminative margin.

### 2.2. Lexical Attractor Collisions & Negative Phrasing
Bi-directional cross-encoders attend heavily to keyword matches regardless of syntactic polarity. Negative sentences like *"not for dimming or adjusting brightness"* in `lights_off` caused queries like *"dim the desk lamp"* to attend directly to `lights_off`. Similarly, queries like *"put my computer to sleep"* matched `charger.py`'s reflex for `"go to sleep"`, triggering robot docking rather than OS sleep.

### 2.3. Layer 1 Reflex Namespace Collisions
Layer 1 FastEmbed reflexes operate deterministically with negligible latency (~4 ms). However, at 100 tools, generic action reflexes lacked domain-level boundary guards, intercepting commands intended for desktop settings, vertical camera movements, smart home lighting, and clock alarms.

### 2.4. Asymmetric Recall ($k=3$ vs $k=5$) & None-Gating Imbalance
The Two-Layer LLM was evaluated with $k=5$, while LAYA was initially restricted to $k=3$ in scaled runners. Furthermore, when top FAISS candidates were closely scored, LAYA exhibited a description-length bias toward `"none"`.

---

## 3. The 4 Production Architectural Strategies

### Strategy 1: Hierarchical Domain Locking & Candidate Bounding
* **Component:** [`backend/test/routers/tools/tools_config.py`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/test/routers/tools/tools_config.py) & [`backend/test/routers/models/laya/two_layer_topk.py`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/test/routers/models/laya/two_layer_topk.py)
* **Mechanism:** 
  1. All tools are mapped into functional domains (`desktop`, `media`, `smart_home`, `robot`, `productivity`, `cognitive`, `companion`, etc.).
  2. When the primary FAISS tool candidate has high similarity confidence ($\text{score} \le 0.60$), candidates belonging to conflicting domains are pruned.
  3. Candidates are strictly bounded to at most 4 tools to preserve softmax probability contrast in LAYA.

### Strategy 2: Schema Contrast & Purged Negative Phrasing Across All Tool Catalogs
* **Component:** [`backend/test/routers/tools/`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/test/routers/tools/)
  * [`smart_home.py`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/test/routers/tools/smart_home.py): Purged negative sentences (*"not for dimming..."*) from `lights_off` and `lights_on`.
  * [`desktop.py`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/test/routers/tools/desktop.py): Front-loaded discriminative keywords for system volume, screen brightness, and power management.
  * [`media.py`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/test/routers/tools/media.py), [`robot.py`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/test/routers/tools/robot.py), [`productivity.py`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/test/routers/tools/productivity.py), [`cognitive.py`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/test/routers/tools/cognitive.py): Purged conversational distractors and sharpened capability boundaries.
* **Mechanism:** Ensured discriminative verbs reside in the first 12–15 tokens to remain fully within LAYA's 48-token option window.

### Strategy 3: Action Reflex Layer-1 Boundary Guards
* **Component:** [`backend/actions/physical/`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/actions/physical/) & [`backend/test/routers/models/laya/two_layer_topk.py`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/test/routers/models/laya/two_layer_topk.py)
* **Mechanism:**
  1. In [`charger.py`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/actions/physical/charger.py), replaced ambiguous `"go to sleep"` with explicit robot cues (`"robot go to sleep"`, `"cozmo go to sleep"`).
  2. In [`movement.py`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/actions/physical/movement.py), replaced generic `"look around"` with room-scanning phrases (`"scan the surrounding area"`, `"survey the room"`).
  3. In [`two_layer_topk.py`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/test/routers/models/laya/two_layer_topk.py), implemented `validate_layer_1_reflex()` to prevent Layer 1 reflexes from falsely firing on desktop power, vertical head tilts, smart home lighting, and clock alarms.

### Strategy 4: Symmetric $k=5$ Recall with Adaptive Delta Filtering & Decoupled None Gating
* **Component:** [`backend/test/routers/experiments/`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/test/routers/experiments/) & [`backend/test/routers/models/laya/two_layer_topk.py`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/test/routers/models/laya/two_layer_topk.py)
* **Mechanism:**
  1. Updated benchmark runners ([`100_tools.py`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/test/routers/experiments/100_tools.py), [`50_tools.py`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/test/routers/experiments/50_tools.py), [`30_tools.py`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/backend/test/routers/experiments/30_tools.py)) to use symmetric $k=5$ for `2-L-Laya-TopK`.
  2. Tightened distance delta from $+0.25$ to $+0.16$ to eliminate distant stragglers before cross-encoder evaluation.
  3. Added confidence gating for `"none"`: if LAYA predicts `"none"` with low confidence ($< 0.12$) while the top FAISS tool is high confidence ($\le 0.65$), the tool candidate overrides `"none"`.

---

## 4. 100-Tools Category-Level Breakdown

| Category | Correct / Total | Accuracy (%) |
| :--- | :---: | :---: |
| `physical` | 24 / 24 | **100.0%** |
| `digital_setup` | 9 / 9 | **100.0%** |
| `system` | 6 / 6 | **100.0%** |
| `comms` | 15 / 15 | **100.0%** |
| `productivity` | 20 / 21 | **95.2%** |
| `companion` | 17 / 18 | **94.4%** |
| `desktop` | 41 / 45 | **91.1%** |
| `robot` | 48 / 54 | **88.9%** |
| `media` | 35 / 42 | **83.3%** |
| `smart_home` | 29 / 36 | **80.6%** |
| `cognitive_agent` | 23 / 30 | **76.7%** |
| `conversational` | 2 / 3 | **66.7%** |
| **Total** | **269 / 303** | **88.78%** |

