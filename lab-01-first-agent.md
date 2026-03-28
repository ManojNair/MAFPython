# Lab 01 — Your First Agent

## Objective

Build your first AI agent using Microsoft Agent Framework. You'll create an agent that answers questions, learn how to stream responses token-by-token, and understand the core building blocks: **client**, **agent**, and **run**.

---

## Concepts

### The Agent Framework Mental Model

```
┌─────────────────────────────────────────────────┐
│                  Your Application                │
│                                                  │
│   ┌────────────────┐    ┌──────────────────┐     │
│   │  Chat Client   │───►│     Agent        │     │
│   │ (AzureOpenAI   │    │  name, instruct. │     │
│   │  ResponsesAPI) │    │  tools, config   │     │
│   └────────────────┘    └────────┬─────────┘     │
│                                  │               │
│                          agent.run("prompt")     │
│                                  │               │
│                          ┌───────▼───────┐       │
│                          │   Response    │       │
│                          │  .text       │       │
│                          │  .messages   │       │
│                          └───────────────┘       │
└─────────────────────────────────────────────────┘
```

1. **Chat Client** (`AzureOpenAIResponsesClient`): The connection to your Azure OpenAI model. It handles authentication, API calls, and protocol translation.

2. **Agent**: A named entity with instructions (system prompt) that uses the client to process requests. Agents can have tools, session state, and middleware.

3. **Run** (`agent.run()`): Sends a user message to the agent and returns a response. Can be used in non-streaming mode (returns complete response) or streaming mode (yields tokens as they arrive).

### Why AzureOpenAIResponsesClient?

Agent Framework supports multiple client types. We use `AzureOpenAIResponsesClient` because it:
- Supports the latest **Responses API** (successor to Chat Completions)
- Works with all tool types (function tools, code interpreter, web search, MCP)
- Provides native streaming support
- Integrates seamlessly with `DefaultAzureCredential`

---

## Setup

### 1. Create the lab directory and virtual environment

```bash
mkdir -p lab01 && cd lab01
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

### 2. Create `requirements.txt`

```txt
agent-framework --pre
azure-identity
python-dotenv
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env` file

```env
AZURE_OPENAI_ENDPOINT=https://letsaifoundryprj-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5.2
```

---

## Code

Create `main.py`:

```python
"""
Lab 01 — Your First Agent
Microsoft Agent Framework Workshop

Demonstrates:
  - Creating an AzureOpenAIResponsesClient with DefaultAzureCredential
  - Building an agent with name and instructions
  - Running the agent (non-streaming)
  - Running the agent (streaming)
"""

import asyncio
import os

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework.azure import AzureOpenAIResponsesClient

# Load environment variables from .env file
load_dotenv()


async def main():
    # ──────────────────────────────────────────────
    # Step 1: Create the Chat Client
    # ──────────────────────────────────────────────
    # The client is the bridge between your agent and Azure OpenAI.
    # It handles authentication via DefaultAzureCredential, which
    # automatically uses your Azure CLI session.
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    # ──────────────────────────────────────────────
    # Step 2: Create an Agent
    # ──────────────────────────────────────────────
    # An agent wraps the client with a persona (name + instructions).
    # The instructions act as the system prompt — they define the
    # agent's personality, capabilities, and constraints.
    agent = client.as_agent(
        name="HelloAgent",
        instructions=(
            "You are a friendly and knowledgeable assistant. "
            "Keep your answers concise — aim for 2-3 sentences. "
            "If you don't know something, say so honestly."
        ),
    )

    # ──────────────────────────────────────────────
    # Step 3: Non-Streaming Run
    # ──────────────────────────────────────────────
    # agent.run() sends the user's message and waits for the
    # complete response before returning.
    print("=" * 60)
    print("NON-STREAMING RESPONSE")
    print("=" * 60)

    result = await agent.run("What is the capital of France?")
    print(f"Agent: {result}\n")

    # You can also access the structured response:
    # - result.text: the final text content
    # - result.messages: list of all messages in the conversation
    print(f"Response text: {result.text}")
    print(f"Number of messages: {len(result.messages)}")

    # ──────────────────────────────────────────────
    # Step 4: Streaming Run
    # ──────────────────────────────────────────────
    # Streaming returns tokens as they are generated, providing
    # a more responsive user experience. Pass stream=True to
    # agent.run() and iterate over the async generator.
    print("\n" + "=" * 60)
    print("STREAMING RESPONSE")
    print("=" * 60)
    print("Agent: ", end="", flush=True)

    async for chunk in agent.run(
        "Explain quantum computing in simple terms.", stream=True
    ):
        if chunk.text:
            print(chunk.text, end="", flush=True)

    print("\n")

    # ──────────────────────────────────────────────
    # Step 5: Multiple Questions
    # ──────────────────────────────────────────────
    # Each call to agent.run() is independent — there's no
    # conversation memory between calls (we'll fix that in Lab 04).
    print("=" * 60)
    print("MULTIPLE INDEPENDENT QUESTIONS")
    print("=" * 60)

    questions = [
        "What's the largest ocean on Earth?",
        "Who painted the Mona Lisa?",
        "What is 42 * 17?",
    ]

    for question in questions:
        result = await agent.run(question)
        print(f"Q: {question}")
        print(f"A: {result}\n")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Run It

```bash
python main.py
```

### Expected Output

```
============================================================
NON-STREAMING RESPONSE
============================================================
Agent: The capital of France is Paris. It's known for landmarks like the Eiffel Tower and the Louvre Museum.

Response text: The capital of France is Paris...
Number of messages: 2

============================================================
STREAMING RESPONSE
============================================================
Agent: Quantum computing uses quantum bits (qubits) that can be both 0 and 1 at the same time...

============================================================
MULTIPLE INDEPENDENT QUESTIONS
============================================================
Q: What's the largest ocean on Earth?
A: The Pacific Ocean is the largest ocean on Earth...

Q: Who painted the Mona Lisa?
A: Leonardo da Vinci painted the Mona Lisa...

Q: What is 42 * 17?
A: 42 × 17 = 714.
```

---

## Key Takeaways

1. **`AzureOpenAIResponsesClient`** is the bridge between your agent and Azure OpenAI. It handles auth, API calls, and protocol translation.
2. **`client.as_agent()`** creates an agent with a name and instructions (system prompt).
3. **`agent.run(prompt)`** runs the agent with a user message:
   - Without `stream=True` → returns the complete response at once
   - With `stream=True` → yields tokens as they arrive (async generator)
4. **Each `run()` call is independent** — no conversation memory between calls. We'll add session management in Lab 04.

---

## What's Next?

In **[Lab 02 — Function Tools](lab-02-function-tools.md)**, you'll learn how to extend your agent with custom Python functions that the LLM can call — giving it real-world capabilities like checking weather, searching databases, and more.
