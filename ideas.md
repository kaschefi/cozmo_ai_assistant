# 🚀 MoKa AI Assistant: Tool Expansion & Capability Ideas

This document outlines high-value, realistic tool ideas to expand MoKa from **19 tools → 50+ → 100+ tools**, demonstrating the full power of the **Two-Tier Fallback Hierarchy & Dynamic Tool RAG Architecture**.

---

## 🏎️ Tier 1: Instant Reflexes (~45ms, No LLM)
*Best for: Physical robotic animations, instantaneous hardware toggles, media keys, and rapid OS shortcuts.*

### 1. Physical Robot Interactions & Expressive Movements
| Tool Name | Description | Example Voice Trigger |
|---|---|---|
| `cozmo_celebrate` | Raises lift, wiggles tracks in a dance, flashes happy OLED eyes, and plays celebration chime. | *"Celebrate!"*, *"We did it!"*, *"Victory dance"* |
| `cozmo_fist_bump` | Raises lift arm to mid-height, waits for human bumper/lift tap, drops arm with a confirmation beep. | *"Fist bump"*, *"Give me five"* |
| `cozmo_patrol_desk` | Drives a continuous perimeter patrol loop around the desk edge using cliff sensor protection. | *"Patrol the desk"*, *"Guard the area"* |
| `cozmo_head_nod` | Fast vertical head nodding motion to visually affirm statements. | *"Do you agree?"*, *"Nod yes"* |
| `cozmo_head_shake` | Fast horizontal track wiggle to visually decline statements. | *"Shake your head"*, *"Say no"* |
| `cozmo_peekaboo` | Hides face display behind lift arms, pauses, then pops up with a greeting chime. | *"Play peekaboo"*, *"Hide and seek"* |
| `cozmo_flashlight` | Turns on Cozmo's backpack RGB LED / front headlight at maximum white brightness. | *"Flashlight on"*, *"Turn on your light"* |

### 2. Media, Audio & Workstation Shortcuts
| Tool Name | Description | Example Voice Trigger |
|---|---|---|
| `spotify_play_pause` | Toggles media playback for Spotify or active Windows media session. | *"Pause music"*, *"Play my music"* |
| `spotify_skip_track` | Sends global media key to skip to the next song. | *"Next song"*, *"Skip track"* |
| `spotify_prev_track` | Sends global media key to restart or go back to previous song. | *"Previous song"*, *"Go back a track"* |
| `system_volume_set` | Sets master Windows audio volume to a specific percentage (e.g. 20%, 50%, 80%). | *"Set volume to 50%"*, *"Mute sound"* |
| `lock_workstation` | Calls Windows API `LockWorkStation()` to immediately lock the computer. | *"Lock my PC"*, *"Lock my screen"* |
| `take_screenshot` | Captures full desktop screen and saves a timestamped PNG in user pictures. | *"Take a screenshot"*, *"Capture the screen"* |
| `cozmo_dice_roll` | Generates a random number (1–6 or 1–20) and draws the dice graphic on Cozmo's OLED face. | *"Roll a die"*, *"Roll a d20"* |
| `cozmo_coin_flip` | Randomly picks Heads/Tails and displays an animated coin flip on OLED face. | *"Flip a coin"*, *"Heads or tails"* |

### 3. Smart Home & Local IoT Toggles
| Tool Name | Description | Example Voice Trigger |
|---|---|---|
| `toggle_desk_light` | Toggles Philips Hue / Home Assistant smart desk lamp. | *"Toggle desk light"*, *"Turn off desk lamp"* |
| `set_focus_lighting` | Sets smart RGB room lights to cool white (focus) or warm amber (relax). | *"Set lights to focus mode"*, *"Night lighting"* |

---

## 🧠 Tier 2: Cognitive Sub-Agents (~1.1s, Tool Vector RAG + LLM)
*Best for: Multi-step workflows, web queries, database operations, summaries, and API integrations.*

### 4. Productivity, Calendar & Work Integrations
| Tool Name | Description | Example Voice Trigger |
|---|---|---|
| `pomodoro_agent` | Starts a 25-minute focus session with live countdown on Cozmo's OLED face and audio chimes. | *"Start a pomodoro timer"*, *"Begin 25 minute work sprint"* |
| `notion_quick_note` | Appends a note, meeting bullet, or thought to the user's daily Notion journal page. | *"Add a note to Notion: discuss API spec with Alex"*, *"Save this idea"* |
| `gmail_unread_summary` | Queries Gmail API for unread high-priority emails received today and summarizes them. | *"Do I have any important unread emails?"*, *"Summarize today's inbox"* |
| `github_pr_checker` | Queries GitHub REST API for open pull requests, pending review requests, and CI build statuses. | *"What PRs are waiting on my review?"*, *"Check CI build status"* |
| `pdf_document_qa` | Performs local vector RAG over a specified PDF (e.g., lecture slides, research paper) in `docs/`. | *"What does section 3 of the AI paper say about attention?"* |
| `translate_clipboard` | Reads current text in the OS clipboard, detects language, and translates to English/German. | *"Translate what is on my clipboard to English"* |

### 5. Knowledge, Finance & Live Data
| Tool Name | Description | Example Voice Trigger |
|---|---|---|
| `crypto_price_lookup` | Queries CoinGecko / Binance API for real-time Bitcoin, Ethereum, and crypto prices. | *"What is the current price of Bitcoin?"*, *"How much is Solana today?"* |
| `stock_fundamentals_lookup`| Fetches P/E ratio, market cap, and daily earnings performance for any stock ticker. | *"What is Apple's market cap and PE ratio?"* |
| `arxiv_paper_search` | Searches arXiv for recent publications on a given topic and returns top abstracts. | *"Find recent papers on speculative decoding on arXiv"* |
| `wikipedia_summary` | Fetches a clean 2-sentence summary of any historical event, person, or scientific concept. | *"Who was Ada Lovelace?"*, *"Explain quantum entanglement briefly"* |
| `currency_converter` | Real-time foreign exchange rate conversion between world currencies. | *"How much is 500 Euros in Japanese Yen?"* |

### 6. Companion, Games & Security
| Tool Name | Description | Example Voice Trigger |
|---|---|---|
| `cozmo_guard_sentry` | Cozmo monitors camera feed. If motion is detected while user is away, sounds alarm & takes picture. | *"Guard my room while I'm away"*, *"Sentry mode"* |
| `spotify_playlist_selector`| Searches and launches specific mood playlists (*Lofi beats*, *Synthwave coding*, *Workout EDM*). | *"Play some lofi coding beats on Spotify"* |
| `cozmo_trivia_host` | Cozmo asks a trivia question, displays countdown on face, and waits for user's answer. | *"Let's play a trivia game"*, *"Ask me a science trivia question"* |
| `tell_dad_joke` | Generates or fetches a witty, clean programming or dad joke. | *"Tell me a joke"*, *"Make me laugh"* |

---

## 📈 Why This Demonstrates the Two-Tier Scaling Advantage

When scaling from **19 → 50 → 100 tools**:
1. **Zero Prompt Bloat**: All 100 tools are indexed in FAISS vectors. The LLM only ever receives the **top 3 matching candidates** (~360 tokens per call).
2. **Instant Response for High-Frequency Actions**: The ~25 Layer 1 physical actions and presets fire at **~45ms** without touching the LLM.
3. **Graceful Fallback**: Any creative conversational phrasing for any of the 100 tools is caught by Layer 2 at ~1.1s.
