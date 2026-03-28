# Lab 10 — Magentic Orchestration

## Objective

Build the most sophisticated orchestration pattern — **Magentic** — where a manager agent dynamically creates plans, selects specialized agents, tracks progress, and adapts strategy in real time. You'll build a research report automation system with human-in-the-loop plan review.

---

## Concepts

### Magentic Orchestration Pattern

```
                 ┌────────────────────┐
                 │   Manager Agent    │
                 │  (plans & adapts)  │
                 └────────┬───────────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
        ┌─────▼─────┐┌───▼────┐┌─────▼─────┐
        │ Researcher ││ Coder  ││  Writer   │
        │            ││(tools) ││           │
        └────────────┘└────────┘└───────────┘
                          │
               ┌──────────▼──────────┐
               │  Task & Progress    │
               │     Ledger          │
               │  (dynamic plan)     │
               └─────────────────────┘
```

**Execution flow:**
1. **Planning Phase** — Manager analyzes the task and creates an initial plan
2. **Plan Review** (optional HITL) — Humans can review and approve/modify the plan
3. **Agent Selection** — Manager selects the most appropriate agent for each subtask
4. **Execution** — Selected agent works on their assigned portion
5. **Progress Assessment** — Manager evaluates progress and updates the plan
6. **Stall Detection** — If progress stalls, auto-replan or escalate
7. **Iteration** — Steps 3-6 repeat until the task is complete
8. **Final Synthesis** — Manager produces the final consolidated result

**Also known as:** Dynamic Orchestration, Task-Ledger-Based Orchestration, Adaptive Planning

---

## Setup

```bash
mkdir -p lab10 && cd lab10
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
Lab 10 — Magentic Orchestration
Microsoft Agent Framework Workshop

Demonstrates:
  - MagenticBuilder for dynamic multi-agent orchestration
  - Manager agent that creates and adapts plans
  - Progress tracking with MagenticProgressLedger
  - Streaming intermediate agent outputs
  - Human-in-the-loop plan review
"""

import asyncio
import json
import os
from typing import cast

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework import Agent, AgentResponseUpdate, Message, WorkflowEvent
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework.orchestrations import (
    MagenticBuilder,
    MagenticPlanReviewRequest,
    MagenticPlanReviewResponse,
    MagenticProgressLedger,
)

load_dotenv()


async def demo_basic_magentic():
    """Demo 1: Basic Magentic Orchestration without HITL."""
    print("=" * 60)
    print("DEMO 1: Basic Magentic Orchestration")
    print("=" * 60)

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    # Specialized agents
    researcher = client.as_agent(
        name="ResearcherAgent",
        description="Expert in research and information gathering",
        instructions=(
            "You are a Researcher. Gather comprehensive information on the topic. "
            "Provide factual, well-structured research notes with key data points, "
            "statistics, and relevant context. Be thorough but concise."
        ),
    )

    analyst = client.as_agent(
        name="AnalystAgent",
        description="Expert in data analysis and quantitative reasoning",
        instructions=(
            "You are a Data Analyst. Analyze data, perform calculations, "
            "create comparisons, and identify trends. Present findings in "
            "structured format with tables when helpful."
        ),
    )

    writer = client.as_agent(
        name="WriterAgent",
        description="Expert in writing clear, polished reports",
        instructions=(
            "You are a professional Report Writer. Synthesize research and "
            "analysis into a well-structured, readable report. Include an "
            "executive summary, key findings, and recommendations."
        ),
    )

    # Manager agent coordinates the team
    manager = client.as_agent(
        name="MagenticManager",
        description="Orchestrator that coordinates the research team",
        instructions=(
            "You coordinate a team of Researcher, Analyst, and Writer "
            "to produce comprehensive reports. Break tasks into clear steps "
            "and assign them to the right specialist."
        ),
    )

    # Build the Magentic workflow
    workflow = MagenticBuilder(
        participants=[researcher, analyst, writer],
        intermediate_outputs=True,
        manager_agent=manager,
        max_round_count=10,
        max_stall_count=3,
        max_reset_count=2,
    ).build()

    task = (
        "Create a comparative analysis report on the three main cloud providers "
        "(AWS, Azure, GCP) for AI/ML workloads. Compare their AI services, "
        "pricing models, and unique strengths. Recommend the best choice for "
        "a mid-size company starting their AI journey."
    )

    print(f"\n📋 Task: {task}\n")
    print("-" * 60)

    last_message_id: str | None = None
    output_event: WorkflowEvent | None = None

    async for event in workflow.run(task, stream=True):
        if event.type == "output" and isinstance(event.data, AgentResponseUpdate):
            message_id = event.data.message_id
            if message_id != last_message_id:
                if last_message_id is not None:
                    print("\n")
                print(f"🤖 [{event.executor_id}]:", end=" ", flush=True)
                last_message_id = message_id
            print(event.data, end="", flush=True)

        elif event.type == "magentic_orchestrator":
            print(f"\n\n📊 [Magentic Orchestrator] Event: {event.data.event_type.name}")
            if isinstance(event.data.content, Message):
                # Plan message from the manager
                plan_preview = event.data.content.text[:200]
                print(f"   Plan: {plan_preview}...")
            elif isinstance(event.data.content, MagenticProgressLedger):
                # Progress ledger update
                ledger_data = event.data.content.to_dict()
                print(f"   Progress Ledger: {json.dumps(ledger_data, indent=2)[:300]}...")

        elif event.type == "output":
            output_event = event

    # Display final output
    if output_event:
        output_messages = cast(list[Message], output_event.data)
        final_text = output_messages[-1].text if output_messages else "No output"
        print("\n\n" + "=" * 60)
        print("📄 FINAL REPORT")
        print("=" * 60)
        print(final_text)


async def demo_magentic_with_plan_review():
    """Demo 2: Magentic with Human-in-the-Loop Plan Review."""
    print("\n\n" + "=" * 60)
    print("DEMO 2: Magentic with HITL Plan Review")
    print("=" * 60)

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    researcher = client.as_agent(
        name="ResearcherAgent",
        description="Expert in research and information gathering",
        instructions="You are a Researcher. Gather comprehensive information. Be thorough but concise.",
    )

    analyst = client.as_agent(
        name="AnalystAgent",
        description="Expert in data analysis",
        instructions="You are a Data Analyst. Analyze data and identify trends.",
    )

    manager = client.as_agent(
        name="MagenticManager",
        description="Orchestrator for the research team",
        instructions="You coordinate Researcher and Analyst efficiently.",
    )

    # Build with plan review enabled
    workflow = MagenticBuilder(
        participants=[researcher, analyst],
        intermediate_outputs=True,
        enable_plan_review=True,  # HITL: human reviews the plan
        manager_agent=manager,
        max_round_count=8,
        max_stall_count=2,
        max_reset_count=1,
    ).build()

    task = (
        "Research the current state of quantum computing in 2026 "
        "and analyze which industries will be most impacted in the next 5 years."
    )

    print(f"\n📋 Task: {task}\n")
    print("-" * 60)

    pending_request: WorkflowEvent | None = None
    pending_responses: dict[str, MagenticPlanReviewResponse] | None = None
    output_event: WorkflowEvent | None = None

    while not output_event:
        if pending_responses is not None:
            stream = workflow.run(stream=True, responses=pending_responses)
        else:
            stream = workflow.run(task, stream=True)

        last_message_id: str | None = None
        async for event in stream:
            if event.type == "output" and isinstance(event.data, AgentResponseUpdate):
                message_id = event.data.message_id
                if message_id != last_message_id:
                    if last_message_id is not None:
                        print("\n")
                    print(f"🤖 [{event.executor_id}]:", end=" ", flush=True)
                    last_message_id = message_id
                print(event.data, end="", flush=True)

            elif event.type == "request_info" and event.request_type is MagenticPlanReviewRequest:
                pending_request = event

            elif event.type == "output":
                output_event = event

        pending_responses = None

        # Handle plan review request
        if pending_request is not None:
            event_data = cast(MagenticPlanReviewRequest, pending_request.data)
            print("\n\n" + "=" * 60)
            print("📋 PLAN REVIEW REQUEST")
            print("=" * 60)

            if event_data.current_progress is not None:
                print("Current Progress:")
                print(json.dumps(event_data.current_progress.to_dict(), indent=2)[:500])

            print(f"\nProposed Plan:\n{event_data.plan.text[:500]}...")

            # Auto-approve for demo (in real apps, await human input)
            print("\n✅ Plan auto-approved for demo.")
            pending_responses = {pending_request.request_id: event_data.approve()}
            pending_request = None

    # Display final output
    if output_event:
        output_messages = cast(list[Message], output_event.data)
        final_text = output_messages[-1].text if output_messages else "No output"
        print("\n\n" + "=" * 60)
        print("📄 FINAL REPORT")
        print("=" * 60)
        print(final_text[:1000])


async def main():
    await demo_basic_magentic()
    await demo_magentic_with_plan_review()


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

1. **`MagenticBuilder`** creates the most flexible orchestration — dynamic planning with adaptive execution.
2. The **Manager Agent** builds a task ledger, selects agents dynamically, and tracks progress.
3. **`max_round_count`**, **`max_stall_count`**, **`max_reset_count`** prevent infinite loops and stale plans.
4. **`enable_plan_review=True`** adds HITL gates where humans can approve or revise the plan.
5. **`MagenticProgressLedger`** tracks task progress and enables the manager to detect stalls.
6. This pattern is best for **open-ended, complex tasks** where the solution path isn't known in advance.

---

## What's Next?

In **[Lab 11 — Multi-Agent Web App](lab-11-multi-agent-web-app.md)**, you'll combine everything you've learned to build a beautiful, production-ready chat interface using **CopilotKit** and the **AG-UI protocol**.
