# DoubaoCLI

Browser-automation CLI for [豆包 (Doubao)](https://www.doubao.com) — ByteDance's multimodal AI assistant.

**No API key needed.** Uses your existing browser login session via Chrome DevTools Protocol (CDP). Supports chat, file upload (PDF/image analysis), multi-turn Q&A, AI image generation, and 15 skill tools.

## Why browser automation instead of API?

Doubao's REST API is behind ByteDance's `shark_admin` anti-bot system — automated requests get rate-limited (error 710022002) even with valid cookies. But the browser UI works without restrictions. DoubaoCLI connects to your logged-in browser via CDP and interacts through the same DOM elements you click manually — bypassing all anti-bot measures.

## Requirements

| Component | Requirement |
|-----------|-------------|
| **Browser** | Edge, Chrome, or any Chromium-based browser |
| **Browser setup** | Must be launched with `--remote-debugging-port=9222` |
| **Python** | 3.11+ |
| **Playwright** | `pip install playwright && playwright install chromium` |
| **Doubao account** | Logged into doubao.com in the browser |

### Launching your browser with CDP

**Windows (PowerShell)**:
```powershell
Start-Process msedge -ArgumentList '--remote-debugging-port=9222'
```

**macOS**:
```bash
open -a "Google Chrome" --args --remote-debugging-port=9222
```

**Linux**:
```bash
google-chrome --remote-debugging-port=9222 &
```

> **Important**: Close all browser windows first, then launch with the flag. Your existing profile (cookies, logins) is preserved.

## Quick Start

```bash
git clone https://github.com/YOUR_USER/DoubaoCLI.git
cd DoubaoCLI
pip install -r requirements.txt

# Check connection (browser must be running with CDP)
python -m doubaocli status

# Send a message
python -m doubaocli chat "Hello, introduce yourself in one sentence"

# Upload a PDF and ask questions
python -m doubaocli upload paper.pdf --prompt "Summarize this paper"

# Analyze an image
python -m doubaocli image photo.png

# Deep Q&A session (multi-turn, auto-dedup, context management)
python -m doubaocli qa thesis.pdf --rounds 10
```

## Architecture

```
DoubaoCLI/
  doubaocli/
    config.py          # All config via env vars, auto-detect browser CDP
    browser.py         # CDPManager — connect to any Chromium browser
    auth.py            # AuthManager — cookie extraction & validation
    chat.py            # ChatSession — send messages, extract responses
    pacing.py          # HumanPacer — rate limiting (casual/research modes)
    api_client.py      # HTTP fallback (rate-limited, use sparingly)
    modes.py           # Mode & skill switching (15 tools)
    message_actions.py # Copy/like/dislike/regenerate
    conversation.py    # List/open/delete conversations
    deep_think.py      # Super-mode thinking extraction
    file_upload.py     # File upload via hidden <input>
    kb_bridge.py       # Doubao → RAG knowledge base pipeline
    image_gen.py       # AI image generation (/create-image)
    session.py         # QASession — state machine, dedup, context tracking
    conversation_reader.py  # Read full conversation from page DOM
    self_prompt.py     # Smart question generation from knowledge gaps
    deep_qa.py         # DeepQA orchestrator — multi-turn with retry/refresh
    cli.py             # CLI entry point (23 commands)
```

### Data Flow

```
User's Browser (CDP :9222)
    │
    ▼
CDPManager ──► AuthManager ──► ChatSession
    │               │               │
    │               └─ cookies.txt   ├─ send()
    │                                ├─ send_with_file()
    │                                ├─ send_qa()
    └─ Page object                   └─ _wait_for_response()
        │                                │
        ▼                                ▼
  DOM interaction              ChatResult(text, elapsed, error)
  (fill + Enter)               + quality_score (QA mode)
```

### Key Design Decisions

1. **UI path over API**: `locator.fill()` + `locator.press("Enter")` works without rate limits
2. **CDP connection only**: Never launches a browser — connects to user's existing session
3. **DOM row counting for response extraction**: Counts `.list_items > .v_list_row` before sending, waits for new row = assistant reply
4. **State machine for deep Q&A**: ACTIVE→CONTEXT_FULL→new conversation→ACTIVE; dedup via 70% word overlap
5. **Config by env vars**: `DOUBAO_CDP_URL`, `DOUBAO_COOKIE_PATH`, `DOUBAO_CONFIG_DIR`

## Commands

| Command | Description |
|---------|-------------|
| `chat "msg" [--new]` | Send a message |
| `status` | Connection + auth + rate status |
| `upload <file> [--prompt]` | Upload file and ask about it |
| `pdf <file> [--to-kb]` | Analyze PDF or ingest to KB |
| `image <file>` | Describe/analyze an image |
| `qa <file> [--questions ...]` | Deep multi-turn Q&A session |
| `draw "prompt"` | AI image generation |
| `mode quick\|super` | Switch chat mode |
| `skill <name>` | Select skill tool (12 available) |
| `think on\|off` | Deep think via super mode |
| `multi "prompt"` | 5 parallel answer comparison |
| `cookies extract\|validate` | Cookie management |
| `pages [--close\|--clean]` | Manage browser tabs |
| `conversations` | List conversation history |
| `conv --delete <id>` | Delete a conversation |
| `msg like\|dislike\|regenerate` | Message actions |

## Configuration

All paths are configurable via environment variables:

```bash
export DOUBAO_CDP_URL=http://localhost:9222       # CDP endpoint
export DOUBAO_COOKIE_PATH=~/.doubaocli/cookies.txt # Cookie storage
export DOUBAO_CONFIG_DIR=~/.doubaocli              # Config directory
```

## Migrating to Another Web AI Service

DoubaoCLI's architecture is designed for adaptation. Here's the migration guide:

### Step 1: Discover the DOM (1-2 hours)
```python
# Connect to the target service's page via CDP
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    page = browser.contexts[0].pages[0]
    page.goto("https://target-service.com/chat")
    
    # Dump all interactive elements
    print(page.evaluate("""() => {
        const els = document.querySelectorAll('textarea, input, button, [contenteditable]');
        return Array.from(els).map(e => ({
            tag: e.tagName, type: e.type, placeholder: e.placeholder,
            text: e.textContent?.trim()?.substring(0, 30), class: e.className?.substring(0, 60)
        }));
    }"""))
```

### Step 2: Map the interaction pattern
Every chat UI has 3 primitives:
1. **Input**: Find the textarea/ContentEditable selector
2. **Send**: Enter key or click a send button
3. **Response**: Find the message container selector and extraction logic

### Step 3: Adapt the modules (in order)
| DoubaoCLI Module | What to Change |
|-----------------|----------------|
| `config.py` | Replace selectors, service URL, auth indicators |
| `browser.py` | Change `url_filter` and default `ensure_page` URL |
| `chat.py` | Update `_get_last_assistant_text()` JS for the new DOM structure |
| `auth.py` | Update `AUTH_INDICATORS` and domain filters |
| `file_upload.py` | Update `FILE_INPUT_SELECTOR` and `is_file_supported()` |
| Other modules | Mostly reusable as-is — they work at the Page abstraction level |

### Step 4: Common pitfalls
- **v20 App-Bound Encryption**: Chromium 127+ encrypts cookies with a key accessible only to the browser process. You CANNOT decrypt them offline. CDP is the only reliable path.
- **React/Semi-Design inputs**: `keyboard.press("Enter")` may not trigger React synthetic handlers. Use `locator.press("Enter")` on the element directly.
- **Virtual scrolling**: Messages may be scrolled out of view but are still in the DOM. Use `document.querySelectorAll()` not visual inspection.
- **Anti-bot detection**: Never use headless mode. Connect to a real browser with a real profile.

## Troubleshooting (Prompts for Your Coding Agent)

If something doesn't work, send one of these to your coding agent:

### "Browser won't connect"
```
I'm using DoubaoCLI. The browser connection fails with "Cannot connect to Edge at http://localhost:9222". 
My browser IS running. Help me debug this. Steps to try:
1. Check if any browser is listening on port 9222 with curl http://localhost:9222/json/version
2. Verify the browser was launched with --remote-debugging-port=9222 (this flag is NOT remembered between restarts)
3. Close ALL browser windows first, then re-launch with the flag
```

### "I see the page but messages don't send"
```
I'm using DoubaoCLI. The browser is connected and I can see doubao.com, but messages don't send. 
The textarea selector might be wrong. Help me probe the DOM to find the correct selector:
1. Connect via CDP and run page.evaluate() to find all textarea/ContentEditable elements
2. Try each selector with .fill("test") and check if text appears on screen
3. Update TEXTAREA_SELECTORS in config.py with the working selector
```

### "Responses come back but extraction gets the wrong text"
```
I'm using DoubaoCLI. Messages send successfully and I see responses in the browser, but the 
extracted text is wrong (getting my own message back, or getting UI text instead of the reply).
Help me fix the response extraction by:
1. Probing the DOM structure of the chat message list
2. Finding the container that holds individual messages
3. Updating _get_last_assistant_text() in chat.py to target the correct elements
```

### "File uploads don't work"
```
I'm using DoubaoCLI. File upload doesn't work — the file appears to be attached but the AI 
says "you haven't sent me the file". Help me debug:
1. Check if there's a hidden input[type="file"] and what accept types it supports
2. Verify the upload triggers a processing indicator in the DOM
3. Add a wait for the processing indicator before sending the prompt
```

### "Deep Q&A keeps asking duplicate questions"
```
I'm using DoubaoCLI's deep Q&A feature. It asks the same questions multiple times. Help me fix:
1. Check the dedup logic in session.py — is the word overlap threshold too low?
2. Verify conversation_reader.py is actually reading the full conversation history from the DOM
3. Check if has_question_been_asked() uses the right fuzzy matching
```

## Relationship to Memory Forest

DoubaoCLI was developed within the [Memory Forest](https://github.com/YOUR_USER/memory-forest) ecosystem — a structured, layered long-term memory system for AI coding agents. The development process generated:

- **Project memory**: Full architectural decisions, test results, and lessons learned
- **Experience patterns**: Reusable engineering patterns (browser-UI-as-fallback, v20-ABE dead-end, QA session management)
- **Feedback records**: Specific bugs encountered and their root causes

These memories enable future coding agents to understand not just *what* the code does, but *why* each decision was made and *what was tried and failed*.

## License

MIT
