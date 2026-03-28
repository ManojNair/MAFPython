# Lab 04 — Multi-Turn Conversations

## Objective

Give your agent **conversation memory** using sessions. You'll build a personal assistant that remembers context across multiple interactions, and learn how to serialize and restore sessions for persistent conversations.

---

## Concepts

### The Problem: Stateless Runs

In Labs 01-03, each `agent.run()` call was independent — the agent had no memory of previous interactions. This means asking "What's my name?" after introducing yourself would fail.

### The Solution: AgentSession

`AgentSession` is the conversation state container. By creating a session and passing it to each `run()` call, the agent maintains context across turns.

```
Without Session:                    With Session:
                                    
run("I'm Alice") → "Hello!"        run("I'm Alice", session) → "Hello Alice!"
run("What's my name?") → "?"       run("What's my name?", session) → "Alice!"
                                    ↑ Same session = shared context
```

---

## Setup

```bash
mkdir -p lab04 && cd lab04
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### `requirements.txt`

```txt
agent-framework --pre
azure-identity
python-dotenv
```

### `.env`

```env
AZURE_OPENAI_ENDPOINT=https://letsaifoundryprj-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5.2
```

---

## Code

Create `main.py`:

```python
"""
Lab 04 — Multi-Turn Conversations
Microsoft Agent Framework Workshop

Demonstrates:
  - Creating and using AgentSession for conversation memory
  - Multi-turn context preservation
  - Session serialization and restoration
  - Multiple independent sessions
"""

import asyncio
import json
import os

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework import AgentSession
from agent_framework.azure import AzureOpenAIResponsesClient

load_dotenv()


async def demo_multi_turn():
    """Demo 1: Basic multi-turn conversation with session."""
    print("=" * 60)
    print("DEMO 1: Multi-Turn Conversation")
    print("=" * 60)

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    agent = client.as_agent(
        name="PersonalAssistant",
        instructions=(
            "You are a friendly personal assistant. Remember everything the "
            "user tells you and use that context in future responses. "
            "Be conversational and reference previous topics when relevant."
        ),
    )

    # Create a session — this is the key to multi-turn conversations
    session = agent.create_session()

    # Turn 1: Introduction
    print("\n--- Turn 1 ---")
    result = await agent.run("Hi! My name is Alice and I'm a software engineer.", session=session)
    print(f"User: Hi! My name is Alice and I'm a software engineer.")
    print(f"Agent: {result}")

    # Turn 2: Build on context
    print("\n--- Turn 2 ---")
    result = await agent.run("I'm working on a project using Python and Azure.", session=session)
    print(f"User: I'm working on a project using Python and Azure.")
    print(f"Agent: {result}")

    # Turn 3: The agent should remember everything
    print("\n--- Turn 3 ---")
    result = await agent.run("What do you know about me so far?", session=session)
    print(f"User: What do you know about me so far?")
    print(f"Agent: {result}")

    # Turn 4: Follow-up that requires context
    print("\n--- Turn 4 ---")
    result = await agent.run("Can you suggest some Azure services for my project?", session=session)
    print(f"User: Can you suggest some Azure services for my project?")
    print(f"Agent: {result}\n")


async def demo_session_serialization():
    """Demo 2: Serialize and restore sessions."""
    print("=" * 60)
    print("DEMO 2: Session Serialization & Restoration")
    print("=" * 60)

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    agent = client.as_agent(
        name="PersistentAssistant",
        instructions="You are a helpful assistant that remembers all context.",
    )

    # --- Phase 1: Start a conversation ---
    print("\n--- Phase 1: Original conversation ---")
    session = agent.create_session()

    result = await agent.run("Remember this: the secret code is ALPHA-7742.", session=session)
    print(f"User: Remember this: the secret code is ALPHA-7742.")
    print(f"Agent: {result}")

    result = await agent.run("Also remember: the meeting is on Friday at 3pm.", session=session)
    print(f"User: Also remember: the meeting is on Friday at 3pm.")
    print(f"Agent: {result}")

    # --- Phase 2: Serialize the session ---
    print("\n--- Phase 2: Serializing session ---")
    serialized = session.to_dict()
    session_json = json.dumps(serialized, indent=2, default=str)
    print(f"Session serialized to JSON ({len(session_json)} chars)")

    # In a real app, you'd save this to a database, file, or Redis
    # For demo purposes, we just keep it in memory

    # --- Phase 3: Restore and continue ---
    print("\n--- Phase 3: Restored conversation (simulating app restart) ---")
    # Create a brand new agent (simulating a fresh start)
    restored_session = AgentSession.from_dict(serialized)

    result = await agent.run("What's the secret code and when is the meeting?", session=restored_session)
    print(f"User: What's the secret code and when is the meeting?")
    print(f"Agent: {result}\n")


async def demo_multiple_sessions():
    """Demo 3: Multiple independent sessions."""
    print("=" * 60)
    print("DEMO 3: Multiple Independent Sessions")
    print("=" * 60)

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    agent = client.as_agent(
        name="MultiSessionAgent",
        instructions="You are a helpful assistant. Remember the user's context within this conversation.",
    )

    # Create two independent sessions (like two different users)
    session_alice = agent.create_session()
    session_bob = agent.create_session()

    # Alice's conversation
    print("\n--- Alice's Session ---")
    result = await agent.run("I'm Alice and I love Python.", session=session_alice)
    print(f"Alice: I'm Alice and I love Python.")
    print(f"Agent: {result}")

    # Bob's conversation (completely independent)
    print("\n--- Bob's Session ---")
    result = await agent.run("I'm Bob and I prefer JavaScript.", session=session_bob)
    print(f"Bob: I'm Bob and I prefer JavaScript.")
    print(f"Agent: {result}")

    # Each session maintains its own context
    print("\n--- Back to Alice ---")
    result = await agent.run("What language do I prefer?", session=session_alice)
    print(f"Alice: What language do I prefer?")
    print(f"Agent: {result}")

    print("\n--- Back to Bob ---")
    result = await agent.run("What language do I prefer?", session=session_bob)
    print(f"Bob: What language do I prefer?")
    print(f"Agent: {result}\n")


async def main():
    await demo_multi_turn()
    await demo_session_serialization()
    await demo_multiple_sessions()


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
DEMO 1: Multi-Turn Conversation
============================================================

--- Turn 1 ---
User: Hi! My name is Alice and I'm a software engineer.
Agent: Hello Alice! Nice to meet you! It's great to connect with a fellow software engineer.

--- Turn 2 ---
User: I'm working on a project using Python and Azure.
Agent: That's a great stack, Alice! Python and Azure work really well together...

--- Turn 3 ---
User: What do you know about me so far?
Agent: Here's what I know about you, Alice:
- You're a software engineer
- You're working on a project using Python and Azure

--- Turn 4 ---
User: Can you suggest some Azure services for my project?
Agent: Based on your Python + Azure project, here are some suggestions...

============================================================
DEMO 2: Session Serialization & Restoration
============================================================

--- Phase 1: Original conversation ---
...
--- Phase 2: Serializing session ---
Session serialized to JSON (1284 chars)

--- Phase 3: Restored conversation (simulating app restart) ---
User: What's the secret code and when is the meeting?
Agent: The secret code is ALPHA-7742 and the meeting is on Friday at 3pm.

============================================================
DEMO 3: Multiple Independent Sessions
============================================================

--- Back to Alice ---
Alice: What language do I prefer?
Agent: You mentioned that you love Python!

--- Back to Bob ---
Bob: What language do I prefer?
Agent: You said you prefer JavaScript!
```

---

## Key Takeaways

1. **`agent.create_session()`** creates a new conversation context.
2. **Pass `session=session`** to every `agent.run()` call to maintain context across turns.
3. **`session.to_dict()`** serializes the session to a dictionary — save it to a database, file, or cache for persistence.
4. **`AgentSession.from_dict(data)`** restores a session from a serialized dictionary.
5. **Multiple sessions are independent** — perfect for serving multiple users with the same agent.
6. Without a session, each `run()` is stateless and independent.

---

## What's Next?

In **[Lab 05 — Agent as Tool](lab-05-agent-as-tool.md)**, you'll learn how to **compose agents** — using one agent as a tool for another, creating hierarchical agent systems.
