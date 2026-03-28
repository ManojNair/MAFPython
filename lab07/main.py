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

    fundamental = client.as_agent(
        name="FundamentalAnalyst",
        instructions=(
            "You are a fundamental stock analyst. Analyze the given stock by:\n"
            "1. Revenue and earnings trends\n"
            "2. Balance sheet health\n"
            "3. Competitive positioning and moat\n"
            "4. Management quality\n"
            "5. Valuation metrics (P/E, P/S, PEG)\n\n"
            "Provide a bull/bear case. Rate: Strong Buy, Buy, Hold, Sell, or Strong Sell.\n"
            "Keep under 200 words."
        ),
    )

    technical = client.as_agent(
        name="TechnicalAnalyst",
        instructions=(
            "You are a technical stock analyst. Analyze using:\n"
            "1. Price trend and momentum (SMA, EMA)\n"
            "2. Volume analysis\n"
            "3. Support and resistance levels\n"
            "4. RSI and MACD signals\n"
            "5. Chart patterns\n\n"
            "Provide short-term and medium-term outlook.\n"
            "Rate: Bullish, Slightly Bullish, Neutral, Slightly Bearish, or Bearish.\n"
            "Keep under 200 words."
        ),
    )

    sentiment = client.as_agent(
        name="SentimentAnalyst",
        instructions=(
            "You are a market sentiment analyst. Evaluate based on:\n"
            "1. Recent news and media coverage\n"
            "2. Social media buzz and retail investor sentiment\n"
            "3. Analyst consensus and price targets\n"
            "4. Institutional investor activity\n"
            "5. Market narrative and momentum\n\n"
            "Rate: Very Positive, Positive, Neutral, Negative, or Very Negative.\n"
            "Keep under 200 words."
        ),
    )

    esg = client.as_agent(
        name="ESGAnalyst",
        instructions=(
            "You are an ESG analyst. Evaluate:\n"
            "1. Environmental impact and climate commitments\n"
            "2. Social responsibility\n"
            "3. Governance quality\n"
            "4. ESG rating and sustainability risks\n"
            "5. Impact on long-term investment thesis\n\n"
            "Rate: Excellent, Good, Average, Below Average, or Poor.\n"
            "Keep under 200 words."
        ),
    )

    # Demo 1: Default aggregation
    print("=" * 60)
    print("DEMO 1: Concurrent Analysis (Default Aggregation)")
    print("=" * 60)

    workflow = ConcurrentBuilder(participants=[fundamental, technical, sentiment, esg]).build()
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

    # Demo 2: Custom aggregator
    print("\n\n" + "=" * 60)
    print("DEMO 2: Concurrent Analysis (Custom Aggregator)")
    print("=" * 60)

    summarizer = client.as_agent(
        name="InvestmentSummarizer",
        instructions=(
            "You are a senior investment advisor. Synthesize multiple analyst "
            "reports into a clear, actionable recommendation.\n\n"
            "Format:\n"
            "## Overall Recommendation: [Strong Buy/Buy/Hold/Sell/Strong Sell]\n"
            "## Confidence: [High/Medium/Low]\n"
            "## Key Takeaways (3-5 bullets)\n"
            "## Risk Factors\n"
            "## Suggested Action\n\n"
            "Keep under 300 words."
        ),
    )

    async def summarize_results(results: list[AgentExecutorResponse]) -> str:
        expert_sections: list[str] = []
        for r in results:
            messages = getattr(r.agent_response, "messages", [])
            final_text = messages[-1].text if messages else "(no content)"
            expert_sections.append(f"### {r.executor_id}:\n{final_text}")

        combined = "Synthesize these analyst reports:\n\n" + "\n\n".join(expert_sections)
        response = await summarizer.run(combined)
        return response.messages[-1].text if response.messages else ""

    workflow_agg = (
        ConcurrentBuilder(participants=[fundamental, technical, sentiment, esg])
        .with_aggregator(summarize_results)
        .build()
    )

    output = None
    async for event in workflow_agg.run(prompt, stream=True):
        if event.type == "output":
            output = event.data

    if output:
        print("\n===== CONSOLIDATED INVESTMENT RECOMMENDATION =====")
        print(output)

    print()


if __name__ == "__main__":
    asyncio.run(main())
