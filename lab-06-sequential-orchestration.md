# Lab 06 — Sequential Orchestration

## Objective

Build your first **multi-agent workflow** using the Sequential orchestration pattern. You'll create a blog post creation pipeline where agents execute in a defined order — each building upon the output of the previous agent.

---

## Concepts

### Sequential Orchestration Pattern

```
┌──────┐    ┌──────┐    ┌──────┐    ┌──────────┐
│Resear│───►│Writer│───►│Editor│───►│SEO Optim.│───► Final
│cher  │    │      │    │      │    │          │     Output
└──────┘    └──────┘    └──────┘    └──────────┘
     ▲           ▲           ▲           ▲
   Full       Full        Full        Full
   context    context     context     context
              (accumulated from previous agents)
```

**Key characteristics:**
- Agents execute **one after another** in a predefined order
- Each agent sees the **full conversation history** from all previous agents
- Output from each agent **accumulates** — later agents can reference earlier contributions
- The execution order is **deterministic** — defined at build time, not by the agents

**Also known as:** Pipeline, Prompt Chaining, Linear Delegation

### When to Use Sequential Orchestration

| ✅ Use When | ❌ Avoid When |
|-------------|---------------|
| Clear linear dependencies exist | Stages are embarrassingly parallel |
| Each stage builds on the previous | Only a few stages; single agent suffices |
| Progressive refinement is needed | Dynamic routing based on content is needed |
| Deterministic, predictable flow | Agents need to collaborate/debate |

### SequentialBuilder API

```python
from agent_framework.orchestrations import SequentialBuilder

workflow = SequentialBuilder(
    participants=[agent_a, agent_b, agent_c]  # Order matters!
).build()

# Run and collect results
async for event in workflow.run("input prompt", stream=True):
    if event.type == "output":
        final_messages = event.data
```

---

## Setup

```bash
mkdir -p lab06 && cd lab06
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
Lab 06 — Sequential Orchestration
Microsoft Agent Framework Workshop

Demonstrates:
  - SequentialBuilder for pipeline workflows
  - Blog post creation: Researcher → Writer → Editor → SEO Optimizer
  - Streaming workflow events
  - Custom Executor mixed with agents
"""

import asyncio
import os
from typing import cast

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework import Message, WorkflowEvent
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework.orchestrations import SequentialBuilder

load_dotenv()


async def main():
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    # ── Agent 1: Researcher ──
    # Gathers facts and key points about the topic
    researcher = client.as_agent(
        name="Researcher",
        instructions=(
            "You are an expert researcher. Given a blog post topic, provide:\n"
            "1. Key facts and statistics (cite plausible sources)\n"
            "2. Main arguments or angles to cover\n"
            "3. Target audience insights\n"
            "4. 3-5 key points the article should address\n\n"
            "Be thorough but concise. Present your research as structured notes."
        ),
    )

    # ── Agent 2: Writer ──
    # Takes the research and drafts a blog post
    writer = client.as_agent(
        name="Writer",
        instructions=(
            "You are a skilled blog writer. Using the research notes provided "
            "by the Researcher, write a compelling blog post that:\n"
            "1. Has an attention-grabbing headline\n"
            "2. Opens with a hook\n"
            "3. Covers all key points from the research\n"
            "4. Uses clear, engaging prose\n"
            "5. Ends with a strong conclusion and call to action\n\n"
            "Target length: 400-600 words. Write in a professional yet accessible tone."
        ),
    )

    # ── Agent 3: Editor ──
    # Reviews and improves the draft
    editor = client.as_agent(
        name="Editor",
        instructions=(
            "You are a meticulous editor. Review the blog post draft and:\n"
            "1. Fix any grammatical or stylistic issues\n"
            "2. Improve clarity and flow\n"
            "3. Ensure logical structure\n"
            "4. Strengthen weak arguments\n"
            "5. Verify consistency in tone\n\n"
            "Provide the COMPLETE edited version of the post (not just suggestions)."
        ),
    )

    # ── Agent 4: SEO Optimizer ──
    # Optimizes the final post for search engines
    seo_optimizer = client.as_agent(
        name="SEOOptimizer",
        instructions=(
            "You are an SEO specialist. Take the edited blog post and:\n"
            "1. Suggest an SEO-optimized title (with primary keyword)\n"
            "2. Write a meta description (155 chars max)\n"
            "3. Suggest 5-8 relevant keywords/tags\n"
            "4. Add internal linking suggestions\n"
            "5. Provide the final post with strategic keyword placement\n\n"
            "Present the SEO metadata separately, then the final optimized post."
        ),
    )

    # ── Build the Sequential Workflow ──
    # Order matters! Agents execute in the order specified.
    workflow = SequentialBuilder(
        participants=[researcher, writer, editor, seo_optimizer]
    ).build()

    # ── Run the Workflow ──
    topic = (
        "Write a blog post about how AI agents are transforming software development "
        "in 2026, focusing on multi-agent orchestration patterns."
    )

    print("=" * 60)
    print("SEQUENTIAL ORCHESTRATION: Blog Post Pipeline")
    print("=" * 60)
    print(f"\nTopic: {topic}\n")
    print("-" * 60)

    # Stream events and capture the final output
    outputs: list[list[Message]] = []
    async for event in workflow.run(topic, stream=True):
        if event.type == "output":
            outputs.append(cast(list[Message], event.data))

    # Display the pipeline results
    if outputs:
        # The last output contains the full conversation
        final_conversation = outputs[-1]

        for msg in final_conversation:
            name = msg.author_name or ("user" if msg.role == "user" else "assistant")
            print(f"\n{'='*60}")
            print(f"[{name}]")
            print(f"{'='*60}")
            print(msg.text)


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
SEQUENTIAL ORCHESTRATION: Blog Post Pipeline
============================================================

Topic: Write a blog post about how AI agents are transforming...

------------------------------------------------------------

============================================================
[user]
============================================================
Write a blog post about how AI agents are transforming...

============================================================
[Researcher]
============================================================
## Research Notes: AI Agents in Software Development (2026)

### Key Facts:
- The AI agent market is projected to reach $XX billion by 2027...
- Microsoft Agent Framework combines AutoGen + Semantic Kernel...

### Key Points to Cover:
1. Single agent vs multi-agent architectures
2. Five orchestration patterns (sequential, concurrent, handoff, group chat, magentic)
...

============================================================
[Writer]
============================================================
# How AI Agents Are Rewriting the Rules of Software Development

In 2026, the question isn't whether AI will change how we build software...
[Full blog draft]

============================================================
[Editor]
============================================================
# How AI Agents Are Rewriting the Rules of Software Development

[Improved, polished version of the blog post]

============================================================
[SEOOptimizer]
============================================================
## SEO Metadata
- **Title**: AI Agents in Software Development: Multi-Agent Orchestration Patterns (2026)
- **Meta description**: Discover how AI agents and multi-agent...
- **Keywords**: AI agents, multi-agent orchestration, ...

## Final Optimized Post
[SEO-optimized final version]
```

---

## Key Takeaways

1. **`SequentialBuilder(participants=[...])`** creates a pipeline where agents execute in order.
2. **Each agent sees the full conversation** — including all previous agents' outputs.
3. Output **accumulates progressively** — Researcher → Writer builds on research → Editor refines the draft → SEO optimizes the result.
4. Use `stream=True` to get `WorkflowEvent` objects and track progress through the pipeline.
5. The pattern is **deterministic** — the execution order is defined at build time.

---

## What's Next?

In **[Lab 07 — Concurrent Orchestration](lab-07-concurrent-orchestration.md)**, you'll learn the opposite pattern — running multiple agents **in parallel** on the same input and aggregating their results.
