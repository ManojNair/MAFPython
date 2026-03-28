# Lab 09 — Group Chat Orchestration

## Objective

Build a **collaborative multi-agent debate** system where specialized agents discuss a product launch proposal in a shared conversation thread. An orchestrator coordinates who speaks next using both simple selectors and LLM-based selection.

---

## Concepts

### Group Chat Orchestration Pattern

```
                ┌────────────────────┐
                │   Orchestrator     │
                │ (selects speakers) │
                └────────┬───────────┘
                         │
            ┌────────────┼────────────┐
            │            │            │
      ┌─────▼─────┐┌────▼────┐┌─────▼─────┐
      │  Product   ││Engineer ││ Designer  │
      │  Manager   ││         ││           │
      └────────────┘└─────────┘└───────────┘
                         │
               Shared Conversation Thread
               (all agents see all messages)
```

**Key characteristics:**
- **Centralized orchestrator** decides who speaks next (unlike handoff's peer-to-peer)
- **Shared conversation thread** — all agents see the full discussion history
- **Multiple rounds** of interaction for iterative refinement
- Supports **round-robin**, **LLM-based**, or **custom** speaker selection

**Also known as:** Roundtable, Collaborative, Multi-Agent Debate, Council

---

## Setup

```bash
mkdir -p lab09 && cd lab09
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
Lab 09 — Group Chat Orchestration
Microsoft Agent Framework Workshop

Demonstrates:
  - GroupChatBuilder with round-robin speaker selection
  - Agent-based orchestrator for intelligent speaker selection
  - Termination conditions
  - Streaming workflow events with AgentResponseUpdate
"""

import asyncio
import os
from typing import cast

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework import AgentResponseUpdate, Message, Role
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework.orchestrations import GroupChatBuilder, GroupChatState

load_dotenv()


async def demo_round_robin():
    """Demo 1: Group Chat with round-robin speaker selection."""
    print("=" * 60)
    print("DEMO 1: Round-Robin Group Chat")
    print("=" * 60)

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    # Define specialized agents for a product launch review
    product_manager = client.as_agent(
        name="ProductManager",
        instructions=(
            "You are a Product Manager reviewing a feature proposal. Focus on:\n"
            "- User value and market fit\n"
            "- Business metrics and success criteria\n"
            "- Prioritization and roadmap impact\n\n"
            "Be constructive but push for clarity. Keep responses under 150 words."
        ),
    )

    engineer = client.as_agent(
        name="Engineer",
        instructions=(
            "You are a Senior Engineer reviewing a feature proposal. Focus on:\n"
            "- Technical feasibility and architecture\n"
            "- Performance and scalability concerns\n"
            "- Implementation complexity and timeline\n"
            "- Technical debt and maintenance burden\n\n"
            "Be specific about technical challenges. Keep responses under 150 words."
        ),
    )

    designer = client.as_agent(
        name="Designer",
        instructions=(
            "You are a UX Designer reviewing a feature proposal. Focus on:\n"
            "- User experience and interaction design\n"
            "- Accessibility and inclusivity\n"
            "- Visual consistency and design system alignment\n"
            "- User research and testing needs\n\n"
            "Think from the user's perspective. Keep responses under 150 words."
        ),
    )

    qa_lead = client.as_agent(
        name="QALead",
        instructions=(
            "You are a QA Lead reviewing a feature proposal. Focus on:\n"
            "- Test strategy and coverage\n"
            "- Edge cases and failure modes\n"
            "- Regression risks\n"
            "- Quality gates and acceptance criteria\n\n"
            "Identify risks others might miss. Keep responses under 150 words."
        ),
    )

    # Round-robin selector — each agent speaks in order
    def round_robin_selector(state: GroupChatState) -> str:
        participant_names = list(state.participants.keys())
        return participant_names[state.current_round % len(participant_names)]

    # Build the group chat with round-robin selection
    workflow = GroupChatBuilder(
        participants=[product_manager, engineer, designer, qa_lead],
        termination_condition=lambda conversation: len(conversation) >= 5,
        selection_func=round_robin_selector,
    ).build()

    # Run the group chat
    task = (
        "Review this feature proposal: We want to add an AI-powered 'Smart Search' "
        "feature to our e-commerce platform. It would use natural language understanding "
        "to let customers describe what they want in plain English (e.g., 'a red dress "
        "for a summer wedding under $100') and return highly relevant results. "
        "The feature would replace the existing keyword search on mobile and web."
    )

    print(f"\n📋 Proposal: {task}\n")
    print("-" * 60)

    final_conversation: list[Message] = []
    last_executor_id: str | None = None

    async for event in workflow.run_stream(task):
        if event.type == "output" and isinstance(event.data, AgentResponseUpdate):
            eid = event.executor_id
            if eid != last_executor_id:
                if last_executor_id is not None:
                    print()
                print(f"\n🗣️  [{eid}]:", end=" ", flush=True)
                last_executor_id = eid
            print(event.data, end="", flush=True)
        elif event.type == "output":
            final_conversation = cast(list[Message], event.data)

    print("\n\n" + "-" * 60)
    print(f"Discussion ended after {len(final_conversation)} messages.")


async def demo_orchestrator_agent():
    """Demo 2: Group Chat with LLM-based orchestrator."""
    print("\n\n" + "=" * 60)
    print("DEMO 2: Agent-Based Orchestrator Group Chat")
    print("=" * 60)

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    # Maker-Checker pattern: Writer + Reviewer
    writer = client.as_agent(
        name="Writer",
        instructions=(
            "You are a technical writer. Write clear, accurate documentation. "
            "When the Reviewer gives feedback, revise your content accordingly. "
            "Keep outputs focused and under 200 words."
        ),
    )

    reviewer = client.as_agent(
        name="Reviewer",
        instructions=(
            "You are a documentation reviewer. Review the Writer's content for:\n"
            "- Accuracy and completeness\n"
            "- Clarity and readability\n"
            "- Proper formatting\n\n"
            "If the content is good, say 'APPROVED' clearly. "
            "Otherwise, provide specific feedback for improvement. "
            "Keep reviews under 100 words."
        ),
    )

    # LLM-based orchestrator decides who speaks
    orchestrator_agent = client.as_agent(
        name="Orchestrator",
        instructions=(
            "You coordinate a Writer and Reviewer to produce quality documentation.\n\n"
            "Guidelines:\n"
            "- Start with Writer to create the initial draft\n"
            "- Then have Reviewer evaluate the content\n"
            "- If Reviewer has feedback, send back to Writer for revisions\n"
            "- If Reviewer says 'APPROVED', you can finish\n"
            "- Maximum 4 rounds to avoid infinite loops"
        ),
    )

    workflow = GroupChatBuilder(
        participants=[writer, reviewer],
        termination_condition=lambda msgs: (
            len(msgs) >= 6
            or any("APPROVED" in m.text.upper() for m in msgs if m.role == "assistant")
        ),
        orchestrator_agent=orchestrator_agent,
    ).build()

    task = (
        "Write a concise API reference entry for a 'POST /api/users' endpoint "
        "that creates a new user account. Include parameters, response codes, "
        "and an example request/response."
    )

    print(f"\n📝 Task: {task}\n")
    print("-" * 60)

    final_conversation: list[Message] = []
    last_executor_id: str | None = None

    async for event in workflow.run_stream(task):
        if event.type == "output" and isinstance(event.data, AgentResponseUpdate):
            eid = event.executor_id
            if eid != last_executor_id:
                if last_executor_id is not None:
                    print()
                print(f"\n🗣️  [{eid}]:", end=" ", flush=True)
                last_executor_id = eid
            print(event.data, end="", flush=True)
        elif event.type == "output":
            final_conversation = cast(list[Message], event.data)

    print("\n\n" + "-" * 60)
    print(f"Maker-checker loop completed in {len(final_conversation)} messages.")


async def main():
    await demo_round_robin()
    await demo_orchestrator_agent()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Run It

```bash
python main.py
```

---

## Key Takeaways

1. **`GroupChatBuilder`** assembles agents in a star topology with a central orchestrator.
2. **`selection_func`** provides simple speaker selection (round-robin, custom logic).
3. **`orchestrator_agent`** uses an LLM to intelligently decide who speaks next.
4. **`termination_condition`** controls when the conversation ends (message count, keyword detection, etc.).
5. **All agents see the full conversation** — context is synchronized after each turn.
6. The **maker-checker loop** (Writer + Reviewer) is a powerful pattern for quality-gated content creation.

---

## What's Next?

In **[Lab 10 — Magentic Orchestration](lab-10-magentic-orchestration.md)**, you'll build the most sophisticated pattern — a manager agent that dynamically plans, delegates, and adapts strategy as the task evolves.
