# Project Knowledge Base Documentation

## Project Overview

**Project Name:** claudekode
**Type:** Python-based AI Agent CLI Application
**Purpose:** A command-line interface for interacting with an AI agent that streams responses using the OpenRouter API with GLM-4.5 model

---

## Project Architecture

### Directory Structure
```
claudekode/
├── main.py                 # Entry point & CLI application
├── agent/
│   ├── agent.py           # Core Agent class for orchestrating AI interactions
│   └── events.py          # Event system for agent communication
├── client/
│   ├── llm_client.py      # LLM API client (OpenRouter)
│   └── response.py        # Response/Event data structures
└── ui/
    └── tui.py             # Terminal UI for streaming output
```

---

## Detailed Component Documentation

### 1. **main.py** - CLI Entry Point

#### Classes

##### `CLI`
- **Purpose:** Main CLI controller that manages the command-line interface and orchestrates agent execution
- **Initialization:** `__init__()`
  - Initializes `Agent` instance (None initially)
  - Initializes `TUI` instance for terminal output

- **Methods:**
  - `async run_single(message: str) -> str | None`
    - Takes a user message as input
    - Creates an Agent instance using async context manager
    - Processes the message and returns result
    - Called when a prompt is provided via CLI

  - `async process_message(message: str)`
    - Processes the message through the agent
    - Streams events from `agent.run(message)`
    - For each `TEXT_DELTA` event, extracts content and passes to TUI for display
    - Handles real-time streaming of responses

#### Functions

- `async run(messages: dict[str,any])`
  - Currently a placeholder (pass statement)
  - Intended for batch message processing

- `main(prompt: str | None)`
  - Click command decorator entry point
  - Command-line argument: `prompt` (optional, user message)
  - If prompt provided: runs `run_single()` and prints result
  - If no prompt: exits with status 1

#### Usage Flow
```
User Input (CLI Argument)
    ↓
main() function
    ↓
CLI.run_single(message)
    ↓
Agent creation
    ↓
CLI.process_message(message)
    ↓
TUI.stream_assistant_delta() → Console output
```

---

### 2. **agent/agent.py** - Core Agent Logic

#### Classes

##### `Agent`
- **Purpose:** Manages the agentic loop for AI interaction, handles event streaming
- **Initialization:** `__init__()`
  - Creates `LLMClient` instance for API communication

- **Methods:**

  - `async run(message: str) -> AsyncGenerator[AgentEvent, None]`
    - Main entry point for agent execution
    - **Flow:**
      1. Yields `AGENT_START` event with user message
      2. Calls `_agentic_loop()` and yields all events
      3. Extracts final response from last event
      4. Yields `AGENT_END` event with final response
    - Returns async generator of `AgentEvent` objects

  - `async _agentic_loop() -> AsyncGenerator[AgentEvent, None]`
    - Core processing loop for AI interaction
    - **Responsibilities:**
      1. Prepares message list: `[{"role":"user", "content":"hello"}]`
      2. Calls `self.client.chat_completion(messages, stream=True)`
      3. Iterates through stream events:
         - `TEXT_DELTA`: Accumulates response text, yields `text_delta` AgentEvent
         - `ERROR`: Yields `agent_error` AgentEvent
      4. After streaming completes, yields `text_complete` AgentEvent
    - Returns accumulated response text

  - `async __aenter__() -> Agent`
    - Async context manager entry
    - Returns self for use in `async with` statements

  - `async __aexit__(exc_type, exc_val, exc_tb) -> None`
    - Async context manager exit
    - Closes LLMClient connection
    - Sets client to None

#### Event Flow in Agent
```
run(message)
  ├─ AGENT_START event
  ├─ _agentic_loop()
  │   ├─ TEXT_DELTA events (streamed from LLM)
  │   ├─ ERROR events (if API fails)
  │   └─ TEXT_COMPLETE event (end of stream)
  └─ AGENT_END event
```

---

### 3. **agent/events.py** - Event System

#### Enums

##### `AgentEventType` (str, Enum)
- **Agent Lifecycle Events:**
  - `AGENT_START`: Agent begins processing
  - `AGENT_END`: Agent finished processing
  - `AGENT_COMPLETE`: Agent task complete
  - `AGENT_ERROR`: Agent encountered error

- **Text Streaming Events:**
  - `TEXT_DELTA`: Chunk of text received
  - `TEXT_COMPLETE`: All text received

- **Tool Events (not yet implemented):**
  - `TOOL_CALL`: Agent requests tool execution
  - `TOOL_RESULT`: Tool execution result

#### Classes

##### `AgentEvent` (Dataclass)
- **Fields:**
  - `type: AgentEventType` - Event classification
  - `data: dict[str, Any]` - Event payload (default empty dict)

- **Factory Methods (Class Methods):**

  1. `agent_start(message: str) -> AgentEvent`
     - Creates AGENT_START event
     - Data: `{"message": message}`

  2. `agent_end(response: str | None = None, usage: TokenUsage | None = None) -> AgentEvent`
     - Creates AGENT_END event
     - Data: `{"response": response, "usage": usage.__dict__ if usage else None}`

  3. `agent_complete() -> AgentEvent`
     - Creates AGENT_COMPLETE event
     - Data: `{"message": "Agent complete"}`

  4. `agent_error(error: str, details: dict[str, any] | None = None) -> AgentEvent`
     - Creates AGENT_ERROR event
     - Data: `{"error": error, "details": details or {}}`

  5. `text_delta(content: str) -> AgentEvent`
     - Creates TEXT_DELTA event
     - Data: `{"content": content}` (single text chunk)

  6. `text_complete(content: str) -> AgentEvent`
     - Creates TEXT_COMPLETE event
     - Data: `{"content": content}` (accumulated full text)

#### Event Usage Pattern
```python
# Creating events
event = AgentEvent.text_delta("Hello")
event = AgentEvent.agent_error("Connection failed")

# Consuming events
if event.type == AgentEventType.TEXT_DELTA:
    content = event.data.get("content", "")
```

---

### 4. **client/llm_client.py** - LLM API Client

#### Classes

##### `LLMClient`
- **Purpose:** Handles communication with OpenRouter API, manages streaming responses, handles retries
- **Configuration:**
  - API Key: `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`
  - Base URL: `https://openrouter.ai/api/v1`
  - Model: `z-ai/glm-4.5-air:free`
  - Max Retries: 3

- **Attributes:**
  - `_client: AsyncOpenAI | None` - OpenAI async client instance
  - `_max_retries: int` - Maximum retry attempts (3)

- **Methods:**

  1. `get_client() -> AsyncOpenAI`
     - Lazy initialization of AsyncOpenAI client
     - Configured with OpenRouter API credentials
     - Returns cached client if already initialized

  2. `async close() -> None`
     - Closes the AsyncOpenAI client
     - Sets `_client` to None for cleanup

  3. `async chat_completion(messages: list[dict[str, Any]], stream: bool = True) -> AsyncGenerator[StreamEvent, None]`
     - **Main method for LLM communication**
     - Takes messages list and stream flag
     - Prepares kwargs with model, messages, and stream settings
     - Implements retry logic with exponential backoff:
       - RateLimitError: Retries with 2^attempt second delay
       - APIConnectionError: Retries with exponential backoff
       - APIError: Yields error event and returns
     - Yields `StreamEvent` for each response chunk or error

  4. `async _stream_response(client: AsyncOpenAI, kwargs: dict[str,Any]) -> AsyncGenerator[StreamEvent, None]`
     - **Handles streaming responses**
     - Makes async API call with `create(**kwargs)`
     - For each chunk from the response stream:
       - Extracts token usage if available → creates `TokenUsage`
       - Extracts text content from delta → yields `TEXT_DELTA` StreamEvent
       - Tracks finish_reason
     - Final yield: `MESSAGE_COMPLETE` event with usage/finish_reason

  5. `async _non_stream_response(client: AsyncOpenAI, kwargs: dict[str,Any]) -> StreamEvent`
     - **Handles non-streaming responses**
     - Attempts API call up to 3 times with exponential backoff
     - Extracts message content and token usage
     - Returns single `MESSAGE_COMPLETE` StreamEvent

#### Retry Logic
```
Attempt 1: Immediate
Attempt 2: Wait 2 seconds
Attempt 3: Wait 4 seconds
Attempt 4: Wait 8 seconds
If all fail: Return ERROR StreamEvent
```

#### API Response Processing
```
Raw OpenRouter Response
    ↓
_stream_response() or _non_stream_response()
    ↓
Extract: text_delta, usage, finish_reason
    ↓
Yield StreamEvent objects
```

---

### 5. **client/response.py** - Response Data Models

#### Classes

##### `TextDelta` (Dataclass)
- **Purpose:** Represents a chunk of streamed text
- **Fields:**
  - `content: str` - The text content chunk
- **Methods:**
  - `__str__() -> str` - Returns the content string

##### `TokenUsage` (Dataclass)
- **Purpose:** Tracks API token consumption for billing
- **Fields:**
  - `prompt_tokens: int` - Tokens in user prompt (default 0)
  - `completion_tokens: int` - Tokens in model response (default 0)
  - `total_tokens: int` - Total tokens used (default 0)
  - `cached_tokens: int` - Tokens from cache (default 0)
- **Methods:**
  - `__add__(other: TokenUsage) -> TokenUsage`
    - Adds two TokenUsage objects
    - Sums all token counts
    - Returns new TokenUsage instance

##### `StreamEventType` (str, Enum)
- **Purpose:** Classifies streaming events
- **Values:**
  - `TEXT_DELTA = "text_delta"` - Chunk of text received
  - `MESSAGE_COMPLETE = "message_complete"` - Response complete
  - `ERROR = "error"` - Error occurred

##### `StreamEvent` (Dataclass)
- **Purpose:** Event from LLM API streaming
- **Fields:**
  - `type: StreamEventType` - Event classification
  - `text_delta: TextDelta | None` - Text chunk (only for TEXT_DELTA)
  - `error: str | None` - Error message (only for ERROR type)
  - `finish_reason: str | None` - Why streaming ended (e.g., "stop")
  - `usage: TokenUsage | None` - Token counts

#### Data Flow
```
LLMClient API Call
    ↓
Parse OpenRouter Response
    ↓
Create StreamEvent (with TextDelta, TokenUsage, etc.)
    ↓
Yield to Agent
    ↓
Agent extracts data for AgentEvent
```

---

### 6. **ui/tui.py** - Terminal User Interface

#### Theme Configuration

**AGENT_THEME** - Rich Theme Dictionary
- **General colors:**
  - `info`: cyan
  - `warning`: yellow
  - `error`: bright_red bold
  - `success`: green
  - `dim`: dim
  - `muted`: grey50
  - `border`: grey35
  - `highlight`: bold cyan

- **Role colors:**
  - `user`: bright_blue bold
  - `assistant`: bright_white

- **Tool colors:**
  - `tool`: bright_magenta bold
  - `tool.read`: cyan
  - `tool.write`: yellow
  - `tool.shell`: magenta
  - `tool.network`: bright_blue
  - `tool.memory`: green
  - `tool.mcp`: bright_cyan

- **Code styling:**
  - `code`: white

#### Classes

##### `TUI` (Terminal User Interface)
- **Purpose:** Handles terminal output and rendering
- **Initialization:** `__init__(console: Console | None = None)`
  - Accepts optional Console instance
  - Falls back to global console via `get_console()` if not provided

- **Methods:**
  - `stream_assistant_delta(content: str) -> None`
    - Prints text to console without newline (`end=""`)
    - Disables markup to prevent formatting issues (`markup=False`)
    - Used for streaming assistant responses in real-time

#### Helper Functions

- `get_console() -> Console`
  - Singleton pattern for global console instance
  - Initializes Console with AGENT_THEME and highlight=False
  - Returns cached instance on subsequent calls
  - Global variable: `_console`

#### Rendering Flow
```
Agent yields TEXT_DELTA event
    ↓
main.process_message() extracts content
    ↓
TUI.stream_assistant_delta(content)
    ↓
Console prints without newline (streaming effect)
    ↓
User sees live text appearing character by character
```

---

## Component Interaction Flow

### Complete Request-Response Cycle

```
1. USER INPUT
   └─ CLI argument: "Your prompt here"

2. ENTRY POINT (main.py)
   └─ CLI.run_single(message)

3. AGENT ORCHESTRATION (agent/agent.py)
   └─ Agent.run(message)
      ├─ Yield: AGENT_START event
      ├─ Call: _agentic_loop()
      └─ Yield: AGENT_END event

4. AGENTIC LOOP (agent/agent.py::_agentic_loop)
   └─ LLMClient.chat_completion(messages, stream=True)

5. LLM API CLIENT (client/llm_client.py)
   ├─ AsyncOpenAI client (OpenRouter)
   ├─ Retry logic (exponential backoff)
   └─ Response parsing → StreamEvent

6. EVENT PROPAGATION
   ├─ StreamEvent (client/response.py)
   │   └─ Converted to AgentEvent (agent/events.py)
   └─ Yielded back through chain

7. CLI PROCESSING (main.py::process_message)
   └─ For each TEXT_DELTA:
      ├─ Extract content
      └─ TUI.stream_assistant_delta(content)

8. TERMINAL OUTPUT (ui/tui.py)
   └─ Console.print(content, end="", markup=False)

9. USER SEES OUTPUT
   └─ Streaming text appears in real-time
```

### Class Dependency Graph

```
main.py::CLI
├── requires: Agent (agent/agent.py)
├── requires: TUI (ui/tui.py)
├── requires: AgentEventType (agent/events.py)
└── requires: AgentEvent (agent/events.py)

agent/agent.py::Agent
├── requires: LLMClient (client/llm_client.py)
├── requires: AgentEvent (agent/events.py)
├── requires: AgentEventType (agent/events.py)
├── requires: StreamEventType (client/response.py)
└── requires: TokenUsage (client/response.py)

client/llm_client.py::LLMClient
├── requires: StreamEvent (client/response.py)
├── requires: StreamEventType (client/response.py)
├── requires: TextDelta (client/response.py)
├── requires: TokenUsage (client/response.py)
└── requires: AsyncOpenAI (openai library)

ui/tui.py::TUI
└── requires: Console (rich library)

agent/events.py::AgentEvent
└── requires: TokenUsage (client/response.py)
```

---

## Data Structures Summary

### Event Objects Hierarchy

```
AgentEvent (agent/events.py)
├─ type: AgentEventType
└─ data: {key: value}
   ├─ AGENT_START: {message: str}
   ├─ AGENT_END: {response: str|None, usage: TokenUsage|None}
   ├─ TEXT_DELTA: {content: str}
   ├─ TEXT_COMPLETE: {content: str}
   ├─ AGENT_ERROR: {error: str, details: dict}
   └─ [AGENT_COMPLETE, TOOL_CALL, TOOL_RESULT: not fully used]

StreamEvent (client/response.py)
├─ type: StreamEventType
├─ text_delta: TextDelta | None
├─ error: str | None
├─ finish_reason: str | None
└─ usage: TokenUsage | None

TextDelta (client/response.py)
└─ content: str

TokenUsage (client/response.py)
├─ prompt_tokens: int
├─ completion_tokens: int
├─ total_tokens: int
└─ cached_tokens: int
```

---

## Key Features

1. **Async/Await Architecture**
   - All I/O operations are asynchronous
   - Real-time streaming of LLM responses
   - Non-blocking event processing

2. **Streaming Response**
   - Text arrives in chunks (TextDelta)
   - Displayed to user as it arrives
   - More responsive UX than waiting for full response

3. **Retry Logic**
   - Handles RateLimitError with exponential backoff
   - Handles APIConnectionError with exponential backoff
   - Graceful error propagation through event system

4. **Event-Driven Architecture**
   - Loose coupling between components
   - Easy to add new event types
   - Clean separation of concerns

5. **Context Manager Pattern**
   - Agent uses `async with` for resource cleanup
   - Ensures API client is properly closed

6. **Rich Terminal UI**
   - Colored output with theme system
   - Supports streaming without buffering
   - Extensible for future UI elements

---

## Configuration & Credentials

### API Configuration (client/llm_client.py)
- **API Key:** Embedded in code (⚠️ security concern)
- **Base URL:** `https://openrouter.ai/api/v1`
- **Model:** `z-ai/glm-4.5-air:free`
- **Retry Attempts:** 3 (configurable via `_max_retries`)

⚠️ **Note:** API key should be moved to environment variables for security.

---

## Future Enhancement Opportunities

1. **Tool Integration**
   - TOOL_CALL and TOOL_RESULT events are defined but not used
   - Framework ready for multi-turn agent with tool use

2. **Message History**
   - Currently hardcoded: `[{"role":"user", "content":"hello"}]`
   - Could implement conversation memory/context

3. **Configuration**
   - API key and model hardcoded
   - Could load from .env or config files

4. **Error Handling**
   - Could add more specific error handlers
   - Better user-facing error messages

5. **UI Features**
   - Loading indicators
   - Progress bars
   - Token usage display
   - Conversation history viewer

6. **Logging**
   - Currently uses print() for debug messages
   - Could implement structured logging

---

## Dependencies

### Core Libraries
- **openai**: OpenAI/OpenRouter API client
- **click**: CLI framework
- **rich**: Terminal styling and formatting
- **asyncio**: Async/await support (Python built-in)

### Python Version
- Requires Python 3.10+ (for union syntax `X | Y`)

---

## Testing Recommendations

1. **Unit Tests**
   - Test AgentEvent factory methods
   - Test TokenUsage addition
   - Test StreamEvent creation

2. **Integration Tests**
   - Test Agent run cycle with mocked LLMClient
   - Test CLI with mocked Agent

3. **API Tests**
   - Test LLMClient with real OpenRouter API
   - Test retry logic (may need rate limiting)
   - Test error handling

4. **UI Tests**
   - Test TUI streaming output
   - Test theme application

---

## Running the Project

```bash
# With message
python main.py "What is Python?"

# Interactive (not yet implemented)
# python main.py
```

---

---

## Q&A - Common Questions & Deep Dives

### Q1: Why does run_single() take a single message and loop with `async for event`?

**Answer:** The message itself is a single string, but `agent.run(message)` returns an **AsyncGenerator** that yields **multiple AgentEvent objects**, not multiple messages.

**Visual Explanation:**
```
Single User Input: "What is Python?"
    ↓
agent.run(message) creates AsyncGenerator
    ↓
Yields multiple AgentEvents:
    1. AGENT_START event
    2. TEXT_DELTA event (chunk: "Python")
    3. TEXT_DELTA event (chunk: " is")
    4. TEXT_DELTA event (chunk: " a...")
    ... more TEXT_DELTA events ...
    N. TEXT_COMPLETE event
    N+1. AGENT_END event
```

The loop iterates over **events from processing that single message**, not over multiple messages.

**Code Flow:**
```python
async def run_single(self, message: str) -> str | None:
    async with Agent() as agent:
        self.agent = agent
        return await self.process_message(message)  # Single message

async def process_message(self, message: str):
    async for event in self.agent.run(message):  # Loop over events, not messages!
        if event.type == AgentEventType.TEXT_DELTA:
            content = event.data.get("content","")
            self.tui.stream_assistant_delta(content)
```

---

### Q2: What happens after `yield AgentEvent.text_delta(content)` and `yield AgentEvent.text_complete(response_text)`?

**Answer:** The `yield` statement creates a pause point that transfers control to the caller.

**Timeline for TEXT_DELTA:**
```
1. _agentic_loop() yields: AgentEvent.text_delta("Python")
    ↓
2. Execution PAUSES at yield
    ↓
3. Control returns to process_message()
    ↓
4. process_message() receives event and prints: "Python"
    ↓
5. process_message() asks for next event (next iteration)
    ↓
6. Execution RESUMES in _agentic_loop() after the yield
    ↓
7. Next iteration of: async for event in self.client.chat_completion()
    ↓
8. Gets next StreamEvent (" is")
    ↓
9. Repeats: yield AgentEvent.text_delta(" is")
```

**Timeline for TEXT_COMPLETE:**
```
1. All chunks from LLM received and processed
    ↓
2. async for loop in _agentic_loop() completes
    ↓
3. response_text accumulated = "Python is a language..."
    ↓
4. _agentic_loop() yields: AgentEvent.text_complete(response_text)
    ↓
5. Control returns to process_message()
    ↓
6. process_message() checks: is it TEXT_DELTA? NO
    ↓
7. Skips the TUI printing
    ↓
8. Continues loop, asks for next event
    ↓
9. Back in _agentic_loop(), after TEXT_COMPLETE yield
    ↓
10. _agentic_loop() function ends
    ↓
11. Control returns to agent.run()
    ↓
12. agent.run() yields AGENT_END with final_response
```

**Key Insight:** Each `yield` is a pause point. The generator yields a value, execution pauses, the caller processes it, then asks for the next value, and execution resumes right after the yield.

---

### Q3: Why is response_text accumulating if we're not printing it?

**Answer:** `response_text` is accumulated for **multiple purposes**, not just console printing.

**What Happens to response_text:**
```
1. _agentic_loop() accumulates: response_text = "Python is..."
        ↓
2. Yields: AgentEvent.text_complete(response_text)
        ↓
3. Goes to: agent.run()
        ↓
4. agent.run() extracts it:
    if event.type == AgentEventType.TEXT_COMPLETE:
      final_response = event.data.get("content")
        ↓
5. Yields: AgentEvent.agent_end(final_response)
        ↓
6. Goes to: process_message()  [Should be captured here]
        ↓
7. Should return to: main()
        ↓
8. main() should use/print it
```

**Current Issues:**
- ❌ `process_message()` doesn't capture `AGENT_END` event
- ❌ Final response is not returned to `main()`
- ❌ It's accumulated but never used by the CLI

**Why Keep response_text If Not Used:**

1. **Design Pattern (Producer-Consumer):**
   - Stream text ASAP (TEXT_DELTA) → User sees it immediately
   - Keep complete response (TEXT_COMPLETE) → Use it later
   - Don't repeat work - accumulate once, use multiple times

2. **Preparation for Future Features:**
   - Conversation history/memory
   - Logging and analytics
   - Response caching
   - Multi-turn agents (need to remember past responses)
   - Database storage

3. **Common in AI Systems:**
   - ChatGPT streams text to user while also saving to database
   - Show real-time updates but keep complete record
   - Separate concerns: display vs. storage

**Comparison: TEXT_DELTA vs TEXT_COMPLETE**

| Event | Purpose | Used By |
|---|---|---|
| **TEXT_DELTA** | Real-time streaming | TUI (prints immediately) |
| **TEXT_COMPLETE** | Final complete response | Future logging/memory/return value |
| **AGENT_END** | Closure event with final response | Should be captured by process_message() |

---

### Q4: Why don't we see duplicate text in output even though response_text keeps accumulating?

**Answer:** We yield **ONLY the delta (new chunk)**, NOT the accumulated text.

**Concrete Example:**
```
API Stream Chunks:
├─ "Python"
├─ " is"
├─ " a"
└─ " language"

Iteration 1:
├─ content = "Python"              ← Only NEW chunk
├─ response_text = "Python"        ← Accumulate it
└─ yield AgentEvent.text_delta("Python")  ← Yield ONLY new chunk
    → Console prints: "Python"

Iteration 2:
├─ content = " is"                 ← Only NEW chunk (not "Python is")
├─ response_text = "Python is"     ← Accumulate it
└─ yield AgentEvent.text_delta(" is")    ← Yield ONLY new chunk
    → Console prints: " is"

Iteration 3:
├─ content = " a"                  ← Only NEW chunk
├─ response_text = "Python is a"   ← Accumulate it
└─ yield AgentEvent.text_delta(" a")     ← Yield ONLY new chunk
    → Console prints: " a"

Iteration 4:
├─ content = " language"           ← Only NEW chunk
├─ response_text = "Python is a language"
└─ yield AgentEvent.text_delta(" language")
    → Console prints: " language"
```

**Total Output:** `"Python" + " is" + " a" + " language"` = `"Python is a language"` ✅

**If we had yielded accumulated text (WRONG):**
```
Iteration 1: yield "Python"
Iteration 2: yield "Python is"           ← Duplicate! "Python" shown again
Iteration 3: yield "Python is a"         ← Duplicate! "Python is" shown again
Iteration 4: yield "Python is a language" ← Duplicate! Everything shown again

Output:** "PythonPython isPython is aPython is a language" ❌
```

**Key Concept: DELTA**
- **Delta** = "the difference" or "the change"
- Each chunk from API is a delta (new addition)
- We send only NEW content via TEXT_DELTA
- We accumulate for completeness via TEXT_COMPLETE

---

### Q5: What triggers the ERROR case in _agentic_loop()?

**Answer:** ERROR events come from `LLMClient` when API exceptions occur after retries are exhausted.

**When Errors Occur:**

**Scenario 1: Rate Limit Error**
```
Attempt 1: RateLimitError → Wait 2 seconds → Retry
Attempt 2: RateLimitError → Wait 4 seconds → Retry
Attempt 3: RateLimitError → Wait 8 seconds → Retry
Attempt 4: RateLimitError → Retries exhausted
    ↓
LLMClient yields: StreamEvent(ERROR, "Max retries exceeded")
    ↓
_agentic_loop() yields: AgentEvent.agent_error("Max retries exceeded")
```

**Scenario 2: Connection Error**
```
Attempt 1: APIConnectionError → Wait 2 seconds → Retry
Attempt 2: APIConnectionError → Wait 4 seconds → Retry
Attempt 3: APIConnectionError → Wait 8 seconds → Retry
Attempt 4: APIConnectionError → Retries exhausted
    ↓
LLMClient yields: StreamEvent(ERROR, "Connection Error")
    ↓
_agentic_loop() yields: AgentEvent.agent_error("Connection Error")
```

**Scenario 3: API Error (No Retry)**
```
API returns error response immediately
    ↓
LLMClient yields: StreamEvent(ERROR, "API Error")
    ↓
_agentic_loop() yields: AgentEvent.agent_error("API Error")
```

**What Happens After ERROR:**
```python
async for event in self.client.chat_completion(messages, True):
    if event.type == StreamEventType.TEXT_DELTA:
        # ... handle text ...

    elif event.type == StreamEventType.ERROR:
         yield AgentEvent.agent_error(event.error or "Unknown error occured")
         # Execution pauses here

# After yield, chat_completion() has returned (loop ends)
# No more events coming

if response_text:
    yield AgentEvent.text_complete(response_text)  # Only if some text was collected
```

**Current Issue:** `process_message()` doesn't display AGENT_ERROR events to user. Should add:
```python
elif event.type == AgentEventType.AGENT_ERROR:
    error = event.data.get("error", "Unknown error")
    self.tui.print_error(error)  # Display error to console
```

---

### Q6: Complete data flow for a single prompt

**Answer:** Here's the full journey:

```
USER INPUT
│
├─ Command: python main.py "What is Python?"
│
└─→ main() function
    │
    ├─ Creates: CLI()
    └─→ CLI.run_single("What is Python?")
        │
        ├─ Creates: async Agent()
        └─→ CLI.process_message("What is Python?")
            │
            ├─ Iterates: async for event in agent.run("What is Python?")
            │
            └─→ agent.run()
                │
                ├─ yield: AgentEvent.agent_start("What is Python?")
                │   └─ process_message checks: TEXT_DELTA? No → Continue
                │
                ├─→ async for event in _agentic_loop()
                │   │
                │   ├─ messages = [{"role":"user", "content":"hello"}]  ⚠️ Hardcoded!
                │   ├─→ client.chat_completion(messages, stream=True)
                │   │   │
                │   │   └─→ LLMClient._stream_response()
                │   │       │
                │   │       ├─ Makes: await client.chat.completions.create()
                │   │       └─ Yields: StreamEvent objects
                │   │
                │   ├─ Loop through StreamEvents:
                │   │   ├─ TEXT_DELTA("Python") → yield AgentEvent.text_delta("Python")
                │   │   │   └─ Back to process_message()
                │   │   │       └─ Prints: "Python"
                │   │   │
                │   │   ├─ TEXT_DELTA(" is") → yield AgentEvent.text_delta(" is")
                │   │   │   └─ Back to process_message()
                │   │   │       └─ Prints: " is"
                │   │   │
                │   │   ├─ ... more TEXT_DELTA events ...
                │   │   │
                │   │   └─ MESSAGE_COMPLETE → Loop exits
                │   │
                │   └─ yield: AgentEvent.text_complete("Python is a language...")
                │       └─ Back to process_message()
                │           └─ Checks: TEXT_DELTA? No → Continue
                │
                └─ yield: AgentEvent.agent_end(final_response)
                    └─ process_message() loop ends
                        └─ ⚠️ But final_response not captured/returned!

CONSOLE OUTPUT
│
└─ "Python is a language..."
   (No final summary because process_message() doesn't return final_response)
```

---

## Document Metadata
- **Last Updated:** 2026-02-23
- **Project Stage:** Early Development
- **Code Coverage:** Core functionality documented
- **Q&A Coverage:** Generator flow, event handling, data accumulation, error handling
