# Lab 07 — Concurrent Orchestration

## Objective

Run multiple agents **in parallel** on the same input and aggregate their diverse perspectives into a unified result. You'll build an investment analysis system where four specialist agents simultaneously analyze a stock from different angles.

---

## Concepts

### Concurrent Orchestration Pattern

```
                    ┌──────────────────┐
                    │   Input Prompt    │
                    └────────┬─────────┘
                ┌────────────┼────────────┐
                ▼            ▼            ▼
        ┌───────────┐ ┌───────────┐ ┌───────────┐
        │Fundamental│ │ Technical │ │ Sentiment │  ... Agent N
        │ Analyst   │ │ Analyst   │ │ Analyst   │
        └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
              │              │              │
              ▼              ▼              ▼
        ┌─────────────────────────────────────────┐
        │           Aggregator                    │
        │  (default: list of messages)            │
        │  (custom: summarizer agent)             │
        └─────────────────────────────────────────┘
```

**Key characteristics:**
- **All agents work simultaneously** on the same input — reducing total latency
- Each agent provides an **independent perspective** — no shared context between them
- Results are **aggregated** via a default list or a custom aggregator function
- Supports both **deterministic** (all agents) and **dynamic** (selected agents) invocation

**Also known as:** Parallel, Fan-out/Fan-in, Scatter-Gather, Map-Reduce

---

## Setup

```bash
mkdir -p lab07 && cd lab07
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
Lab 07 — Concurrent Orchestration
Microsoft Agent Framework Workshop

Demonstrates:
  - ConcurrentBuilder for parallel agent execution
  - Investment analysis with 4 specialist agents
  - Default aggregation (list of messages)
  - Custom aggregator with a summarizer agent
"""

import asyncio
import os
from typing import cast

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework import AgentExecutorResponse, Message, WorkflowEvent
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework.orchestrations import ConcurrentBuilder

load_dotenv()


async def main():
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    # ── Specialist Agent 1: Fundamental Analyst ──
    fundamental = client.as_agent(
        name="FundamentalAnalyst",
        instructions=(
            "You are a fundamental stock analyst. Analyze the given stock/company by:\n"
            "1. Revenue and earnings trends\n"
            "2. Balance sheet health (debt/equity ratio)\n"
            "3. Competitive positioning and moat\n"
            "4. Management quality and strategy\n"
            "5. Valuation metrics (P/E, P/S, PEG)\n\n"
            "Provide a bull/bear case and a rating: Strong Buy, Buy, Hold, Sell, or Strong Sell.\n"
            "Keep analysis under 200 words."
        ),
    )

    # ── Specialist Agent 2: Technical Analyst ──
    technical = client.as_agent(
        name="TechnicalAnalyst",
        instructions=(
            "You are a technical stock analyst. Analyze the given stock using:\n"
            "1. Price trend and momentum (SMA, EMA)\n"
            "2. Volume analysis\n"
            "3. Support and resistance levels\n"
            "4. RSI and MACD signals\n"
            "5. Chart patterns\n\n"
            "Provide a short-term (1-4 weeks) and medium-term (3-6 months) outlook.\n"
            "Rate: Bullish, Slightly Bullish, Neutral, Slightly Bearish, or Bearish.\n"
            "Keep analysis under 200 words."
        ),
    )

    # ── Specialist Agent 3: Sentiment Analyst ──
    sentiment = client.as_agent(
        name="SentimentAnalyst",
        instructions=(
            "You are a market sentiment analyst. Evaluate the given stock based on:\n"
            "1. Recent news and media coverage\n"
            "2. Social media buzz and retail investor sentiment\n"
            "3. Analyst consensus and price targets\n"
            "4. Institutional investor activity\n"
            "5. Market narrative and momentum\n\n"
            "Rate overall sentiment: Very Positive, Positive, Neutral, Negative, or Very Negative.\n"
            "Keep analysis under 200 words."
        ),
    )

    # ── Specialist Agent 4: ESG Analyst ──
    esg = client.as_agent(
        name="ESGAnalyst",
        instructions=(
            "You are an ESG (Environmental, Social, Governance) analyst. Evaluate:\n"
            "1. Environmental impact and climate commitments\n"
            "2. Social responsibility (labor, diversity, community)\n"
            "3. Governance quality (board independence, transparency)\n"
            "4. ESG rating and sustainability risks\n"
            "5. Impact on long-term investment thesis\n\n"
            "Rate ESG profile: Excellent, Good, Average, Below Average, or Poor.\n"
            "Keep analysis under 200 words."
        ),
    )

    # ═══════════════════════════════════════════════
    # DEMO 1: Default Aggregation (list of messages)
    # ═══════════════════════════════════════════════

    print("=" * 60)
    print("DEMO 1: Concurrent Analysis (Default Aggregation)")
    print("=" * 60)

    workflow = ConcurrentBuilder(
        participants=[fundamental, technical, sentiment, esg]
    ).build()

    prompt = "Analyze Microsoft (MSFT) stock for a potential investment."

    output_data: list[Message] | None = None
    async for event in workflow.run(prompt, stream=True):
        if event.type == "output":
            output_data = event.data

    if output_data:
        messages: list[Message] = cast(list[Message], output_data)
        for i, msg in enumerate(messages, start=1):
            name = msg.author_name if msg.author_name else "user"
            print(f"\n{'-' * 60}")
            print(f"{i:02d} [{name}]:")
            print(f"{'-' * 60}")
            print(msg.text)

    # ═══════════════════════════════════════════════
    # DEMO 2: Custom Aggregator with Summarizer Agent
    # ═══════════════════════════════════════════════

    print("\n\n" + "=" * 60)
    print("DEMO 2: Concurrent Analysis (Custom Aggregator)")
    print("=" * 60)

    # Create a summarizer agent for the aggregator
    summarizer = client.as_agent(
        name="InvestmentSummarizer",
        instructions=(
            "You are a senior investment advisor. You receive analyses from multiple "
            "specialist analysts (fundamental, technical, sentiment, ESG). "
            "Synthesize their findings into a clear, actionable investment recommendation.\n\n"
            "Format:\n"
            "## Overall Recommendation: [Strong Buy/Buy/Hold/Sell/Strong Sell]\n"
            "## Confidence: [High/Medium/Low]\n"
            "## Key Takeaways (3-5 bullets)\n"
            "## Risk Factors\n"
            "## Suggested Action\n\n"
            "Keep the summary under 300 words."
        ),
    )

    async def summarize_results(results: list[AgentExecutorResponse]) -> str:
        """Custom aggregator: synthesize all analyst outputs into one recommendation."""
        expert_sections: list[str] = []
        for r in results:
            messages = getattr(r.agent_response, "messages", [])
            final_text = messages[-1].text if messages else "(no content)"
            expert_sections.append(f"### {r.executor_id}:\n{final_text}")

        prompt = "Synthesize these analyst reports:\n\n" + "\n\n".join(expert_sections)
        response = await summarizer.run(prompt)
        return response.messages[-1].text if response.messages else ""

    # Build workflow with custom aggregator
    workflow_with_aggregator = (
        ConcurrentBuilder(participants=[fundamental, technical, sentiment, esg])
        .with_aggregator(summarize_results)
        .build()
    )

    output = None
    async for event in workflow_with_aggregator.run(prompt, stream=True):
        if event.type == "output":
            output = event.data

    if output:
        print("\n===== CONSOLIDATED INVESTMENT RECOMMENDATION =====")
        print(output)

    print()


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
DEMO 1: Concurrent Analysis (Default Aggregation)
============================================================

------------------------------------------------------------
01 [user]:
------------------------------------------------------------
Analyze Microsoft (MSFT) stock for a potential investment.

------------------------------------------------------------
02 [FundamentalAnalyst]:
------------------------------------------------------------
## Fundamental Analysis: Microsoft (MSFT)
Revenue has grown at a CAGR of ~15% driven by Azure cloud...
Rating: **Strong Buy**

------------------------------------------------------------
03 [TechnicalAnalyst]:
------------------------------------------------------------
## Technical Analysis: MSFT
Price is trading above the 50-day and 200-day SMA...
Short-term: **Slightly Bullish** | Medium-term: **Bullish**

------------------------------------------------------------
04 [SentimentAnalyst]:
------------------------------------------------------------
## Sentiment Analysis: MSFT
Overall sentiment is Very Positive driven by AI narrative...
Sentiment: **Very Positive**

------------------------------------------------------------
05 [ESGAnalyst]:
------------------------------------------------------------
## ESG Analysis: MSFT
Microsoft leads in environmental commitments...
ESG Rating: **Excellent**

============================================================
DEMO 2: Concurrent Analysis (Custom Aggregator)
============================================================

===== CONSOLIDATED INVESTMENT RECOMMENDATION =====
## Overall Recommendation: Strong Buy
## Confidence: High

## Key Takeaways
- Strong fundamental growth driven by Azure and AI...
- Technical indicators confirm bullish momentum...
- Market sentiment overwhelmingly positive...
- Industry-leading ESG profile reduces long-term risk...

## Risk Factors
- Premium valuation leaves limited margin of safety...

## Suggested Action
Accumulate on any pullbacks to the 50-day SMA...
```

---

## Key Takeaways

1. **`ConcurrentBuilder(participants=[...])`** runs all agents simultaneously on the same input.
2. By default, results are aggregated as a **flat list of messages** from all agents.
3. **`.with_aggregator(func)`** lets you define custom aggregation logic — like using a summarizer agent.
4. Each agent works **independently** — no shared context between concurrent agents.
5. This pattern **reduces latency** compared to sequential (wall-clock time = slowest agent, not sum of all).
6. Perfect for **diverse analysis**, brainstorming, ensemble reasoning, and voting systems.

---

## What's Next?

In **[Lab 08 — Handoff Orchestration](lab-08-handoff-orchestration.md)**, you'll build an interactive customer support system where agents **dynamically transfer control** to each other based on the conversation context.
