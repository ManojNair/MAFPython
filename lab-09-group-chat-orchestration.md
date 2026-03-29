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

### How Does the Orchestrator Choose Who Speaks?

The `GroupChatBuilder` supports two speaker selection strategies:

| Strategy | How it works | When to use |
|----------|-------------|-------------|
| **`selection_func`** | You provide a Python function that receives the current `GroupChatState` (participants, round number, conversation history) and returns the name of the next speaker. | Deterministic patterns — round-robin, priority-based, or any custom logic. |
| **`orchestrator_agent`** | An LLM-based agent reads the full conversation and decides which participant should speak next based on context. | Dynamic selection — when the "right" next speaker depends on what was just said. |

**Demo 1 uses `selection_func`** with round-robin logic:
```python
def round_robin_selector(state: GroupChatState) -> str:
    names = list(state.participants.keys())
    return names[state.current_round % len(names)]
```
The orchestrator cycles through agents in order: PM → Engineer → Designer → QA → PM → ...

**Demo 2 uses `orchestrator_agent`** — an LLM that reasons about the conversation:
- Sees the Writer just submitted a draft? → Picks the Reviewer.
- Sees the Reviewer gave feedback? → Sends it back to the Writer.
- Sees "APPROVED"? → The termination condition ends the loop.

The orchestrator agent never speaks to the user — it only decides *who* speaks next.

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
  - Tracking which agent speaks each round
"""

import asyncio
import os

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework import Message
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework.orchestrations import GroupChatBuilder, GroupChatState

load_dotenv()


def print_conversation(messages: list[Message], task_text: str) -> None:
    """Print the group chat conversation with clear round markers."""
    round_num = 0
    for msg in messages:
        if msg.role == "user":
            continue  # Skip the initial task message
        round_num += 1
        agent_name = msg.author_name or "Unknown"
        print(f"\n{'─' * 60}")
        print(f"  Round {round_num} │ Agent: {agent_name}")
        print(f"{'─' * 60}")
        if msg.text:
            print(f"  {msg.text}")


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
        selected = participant_names[state.current_round % len(participant_names)]
        print(f"\n  [Orchestrator] Round {state.current_round + 1}: selecting --> {selected}")
        return selected

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

    result = await workflow.run(task)

    # Extract the final conversation from the output event
    conversation: list[Message] = []
    for event in result:
        if event.type == "output" and isinstance(event.data, list):
            conversation = event.data
            break

    print_conversation(conversation, task)

    print("\n\n" + "=" * 60)
    print(f"Discussion ended after {len([m for m in conversation if m.role != 'user'])} agent messages.")
    print("=" * 60)

    # ── Synthesize the discussion into a final recommendation ──

    print("\n  Synthesizing group discussion...\n")

    # Build a transcript of the discussion for the synthesizer
    transcript = "\n\n".join(
        f"[{msg.author_name}]: {msg.text}"
        for msg in conversation
        if msg.role != "user" and msg.text
    )

    synthesizer = client.as_agent(
        name="Synthesizer",
        instructions=(
            "You are a decision facilitator. You've just observed a group discussion "
            "between a Product Manager, Engineer, Designer, and QA Lead reviewing a "
            "feature proposal. Synthesize their input into a clear, actionable "
            "recommendation. Include:\n"
            "- GO / NO-GO / CONDITIONAL GO decision\n"
            "- Key concerns that must be addressed\n"
            "- Suggested next steps\n\n"
            "Keep it under 200 words."
        ),
    )

    synthesis = await synthesizer.run(
        f"Here is the team's discussion on the Smart Search proposal:\n\n{transcript}\n\n"
        f"Please provide your synthesized recommendation."
    )

    print("=" * 60)
    print("  FINAL RECOMMENDATION (synthesized from group discussion)")
    print("=" * 60)
    if synthesis.text:
        print(f"\n  {synthesis.text}")
    print("\n" + "=" * 60)


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

    result = await workflow.run(task)

    # Extract the final conversation from the output event
    conversation: list[Message] = []
    for event in result:
        if event.type == "output" and isinstance(event.data, list):
            conversation = event.data
            break

    # Print with orchestrator reasoning
    round_num = 0
    prev_agent: str | None = None
    for msg in conversation:
        if msg.role == "user":
            continue
        round_num += 1
        agent_name = msg.author_name or "Unknown"

        # Explain WHY the orchestrator chose this agent
        if round_num == 1:
            reason = "No draft exists yet — orchestrator starts with Writer."
        elif agent_name == "Reviewer" and prev_agent == "Writer":
            reason = "Writer submitted content — orchestrator sends to Reviewer for evaluation."
        elif agent_name == "Writer" and prev_agent == "Reviewer":
            reason = "Reviewer gave feedback — orchestrator sends back to Writer for revision."
        elif agent_name == "Reviewer":
            reason = "Writer revised the draft — orchestrator sends to Reviewer to re-evaluate."
        else:
            reason = "Orchestrator selected next speaker based on conversation context."

        print(f"\n  [Orchestrator] {reason}")
        print(f"{'─' * 60}")
        print(f"  Round {round_num} │ Agent: {agent_name}")
        print(f"{'─' * 60}")
        if msg.text:
            print(f"  {msg.text}")
        prev_agent = agent_name

    approved = any(
        "APPROVED" in m.text.upper()
        for m in conversation
        if m.role == "assistant" and m.text
    )

    print("\n\n" + "=" * 60)
    status = "APPROVED" if approved else "max rounds reached"
    print(f"Maker-checker loop completed ({status}) in {len([m for m in conversation if m.role != 'user'])} agent messages.")
    print("=" * 60)


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

### Expected Output

```
============================================================
DEMO 1: Round-Robin Group Chat
============================================================

📋 Proposal: Review this feature proposal: ...

------------------------------------------------------------

  [Orchestrator] Round 1: selecting --> ProductManager

────────────────────────────────────────────────────────────
  Round 1 │ Agent: ProductManager
────────────────────────────────────────────────────────────
  The Smart Search proposal is exciting — NLU-driven discovery
  could significantly boost conversion. I'd want to see success
  metrics defined upfront: search-to-purchase rate, time-to-result...

  [Orchestrator] Round 2: selecting --> Engineer

────────────────────────────────────────────────────────────
  Round 2 │ Agent: Engineer
────────────────────────────────────────────────────────────
  Technically feasible but non-trivial. We'd need an embedding
  pipeline, vector search infrastructure, and a relevance ranking
  model. I'd estimate 3-4 months for MVP...

  [Orchestrator] Round 3: selecting --> Designer

────────────────────────────────────────────────────────────
  Round 3 │ Agent: Designer
────────────────────────────────────────────────────────────
  From a UX perspective, the natural language input is great for
  discoverability. We need to handle empty/ambiguous queries
  gracefully...

  [Orchestrator] Round 4: selecting --> QALead

────────────────────────────────────────────────────────────
  Round 4 │ Agent: QALead
────────────────────────────────────────────────────────────
  Key testing concerns: How do we validate relevance quality?
  We'll need a benchmark dataset and A/B testing framework...


============================================================
Discussion ended after 4 agent messages.
============================================================

  Synthesizing group discussion...

============================================================
  FINAL RECOMMENDATION (synthesized from group discussion)
============================================================

  CONDITIONAL GO — Proceed with Smart Search as a mobile-first MVP.

  Key concerns to address:
  - Engineer: Build embedding pipeline + vector search; estimate
    3-4 months for MVP. Address scalability before desktop rollout.
  - Designer: Handle ambiguous/empty queries gracefully; run
    usability testing with diverse user groups.
  - QA: Create benchmark dataset for relevance scoring; set up
    A/B testing framework to compare against keyword search.

  Suggested next steps:
  1. Define success metrics (search-to-purchase rate, time-to-result)
  2. Spike on vector search infrastructure (2 weeks)
  3. Mobile prototype with 5 user research sessions
  4. QA to build benchmark dataset in parallel

============================================================


============================================================
DEMO 2: Agent-Based Orchestrator Group Chat
============================================================

📝 Task: Write a concise API reference entry for a 'POST /api/users'
endpoint...

------------------------------------------------------------

  [Orchestrator] No draft exists yet — orchestrator starts with Writer.
────────────────────────────────────────────────────────────
  Round 1 │ Agent: Writer
────────────────────────────────────────────────────────────
  ## POST /api/users
  Creates a new user account.
  **Parameters:** ...

  [Orchestrator] Writer submitted content — orchestrator sends to Reviewer for evaluation.
────────────────────────────────────────────────────────────
  Round 2 │ Agent: Reviewer
────────────────────────────────────────────────────────────
  Good structure. Missing: rate limiting info, authentication
  requirements. Add a 409 Conflict response code...

  [Orchestrator] Reviewer gave feedback — orchestrator sends back to Writer for revision.
────────────────────────────────────────────────────────────
  Round 3 │ Agent: Writer
────────────────────────────────────────────────────────────
  ## POST /api/users (revised)
  ...

  [Orchestrator] Writer revised the draft — orchestrator sends to Reviewer to re-evaluate.
────────────────────────────────────────────────────────────
  Round 4 │ Agent: Reviewer
────────────────────────────────────────────────────────────
  APPROVED — comprehensive and well-formatted.


============================================================
Maker-checker loop completed (APPROVED) in 4 agent messages.
============================================================
```

## Key Takeaways

1. **`GroupChatBuilder`** assembles agents in a star topology with a central orchestrator.
2. **`selection_func`** provides simple speaker selection (round-robin, custom logic).
3. **`orchestrator_agent`** uses an LLM to intelligently decide who speaks next.
4. **`termination_condition`** controls when the conversation ends (message count, keyword detection, etc.).
5. **All agents see the full conversation** — context is synchronized after each turn.
6. **Synthesis step** — after the group chat ends, a separate agent can read the full transcript and produce a final recommendation, completing the pattern: *prompt → multi-agent discussion → actionable outcome*.
7. The **maker-checker loop** (Writer + Reviewer) is a powerful pattern for quality-gated content creation.

---

## What's Next?

In **[Lab 10 — Magentic Orchestration](lab-10-magentic-orchestration.md)**, you'll build the most sophisticated pattern — a manager agent that dynamically plans, delegates, and adapts strategy as the task evolves.
