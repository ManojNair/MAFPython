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

    session = agent.create_session()

    conversations = [
        "Hi! My name is Alice and I'm a software engineer.",
        "I'm working on a project using Python and Azure.",
        "What do you know about me so far?",
        "Can you suggest some Azure services for my project?",
    ]

    for i, msg in enumerate(conversations, 1):
        print(f"\n--- Turn {i} ---")
        result = await agent.run(msg, session=session)
        print(f"User: {msg}")
        print(f"Agent: {result}")

    print()


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

    # Phase 1: Start a conversation
    print("\n--- Phase 1: Original conversation ---")
    session = agent.create_session()

    result = await agent.run("Remember this: the secret code is ALPHA-7742.", session=session)
    print(f"User: Remember this: the secret code is ALPHA-7742.")
    print(f"Agent: {result}")

    result = await agent.run("Also remember: the meeting is on Friday at 3pm.", session=session)
    print(f"User: Also remember: the meeting is on Friday at 3pm.")
    print(f"Agent: {result}")

    # Phase 2: Serialize
    print("\n--- Phase 2: Serializing session ---")
    serialized = session.to_dict()
    session_json = json.dumps(serialized, indent=2, default=str)
    print(f"Session serialized to JSON ({len(session_json)} chars)")

    # Phase 3: Restore and continue
    print("\n--- Phase 3: Restored conversation ---")
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

    session_alice = agent.create_session()
    session_bob = agent.create_session()

    print("\n--- Alice's Session ---")
    result = await agent.run("I'm Alice and I love Python.", session=session_alice)
    print(f"Alice: I'm Alice and I love Python.")
    print(f"Agent: {result}")

    print("\n--- Bob's Session ---")
    result = await agent.run("I'm Bob and I prefer JavaScript.", session=session_bob)
    print(f"Bob: I'm Bob and I prefer JavaScript.")
    print(f"Agent: {result}")

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
