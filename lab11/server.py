"""
Lab 11 — Multi-Agent Web App Backend
Microsoft Agent Framework Workshop

AG-UI + FastAPI server that exposes a multi-agent advisory board
as an HTTP endpoint with Server-Sent Events streaming.
"""

import os
from typing import Annotated

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import Field

from agent_framework import tool
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework_ag_ui.fastapi import add_agent_framework_fastapi_endpoint

load_dotenv()

app = FastAPI(title="AI Advisory Board", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Tools ──

@tool(description="Analyze market size and growth potential for a business idea.")
def analyze_market(
    industry: Annotated[str, Field(description="Industry or market segment")],
) -> str:
    """Analyze market opportunity."""
    markets = {
        "ai": "Global AI market: $500B (2026), CAGR 37%. Segments: Enterprise AI, GenAI, AI Agents.",
        "fintech": "Global fintech market: $310B (2026), CAGR 25%. Segments: Digital payments, neobanks.",
        "healthtech": "Global healthtech: $450B (2026), CAGR 22%. Segments: Telehealth, AI diagnostics.",
        "edtech": "Global edtech: $200B (2026), CAGR 18%. Segments: Online learning, AI tutoring.",
    }
    return markets.get(industry.lower(), f"Market for {industry}: Est. $50-100B, growing 15-20% annually.")


@tool(description="Perform financial modeling and ROI analysis.")
def financial_analysis(
    scenario: Annotated[str, Field(description="Business scenario to analyze")],
) -> str:
    """Run financial analysis."""
    return (
        f"Financial Analysis for '{scenario}':\n"
        f"- Initial investment: $500K-2M\n- Break-even: 18-24 months\n"
        f"- Year 1 revenue: $1-3M\n- Year 3 revenue: $10-25M\n- IRR: 35-45%"
    )


@tool(description="Review legal and regulatory considerations.")
def legal_review(
    business_type: Annotated[str, Field(description="Type of business")],
) -> str:
    """Review legal considerations."""
    return (
        f"Legal Review for '{business_type}':\n"
        f"- Entity: Delaware C-Corp recommended\n- IP: File provisionals early\n"
        f"- Compliance: GDPR, SOC2 required\n- Contracts: Standard SaaS terms"
    )


@tool(description="Assess technical feasibility and architecture.")
def tech_assessment(
    project: Annotated[str, Field(description="Project to assess")],
) -> str:
    """Assess technical feasibility."""
    return (
        f"Tech Assessment for '{project}':\n"
        f"- Architecture: Microservices on Azure Container Apps\n"
        f"- AI: Azure OpenAI + Agent Framework\n- Data: Cosmos DB + Data Lake\n"
        f"- Timeline: MVP 3-4 months, production 6-8 months\n- Team: 4-5 engineers"
    )


# ── Agents ──

def create_advisory_agent():
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    strategy_agent = client.as_agent(
        name="StrategyAdvisor",
        description="Business strategy expert.",
        instructions="You are a business strategy advisor. Use analyze_market for data. Be concise and actionable.",
        tools=[analyze_market],
    )

    finance_agent = client.as_agent(
        name="FinanceAdvisor",
        description="Financial expert.",
        instructions="You are a financial advisor. Use financial_analysis for modeling. Be specific with numbers.",
        tools=[financial_analysis],
    )

    legal_agent = client.as_agent(
        name="LegalAdvisor",
        description="Legal expert.",
        instructions="You are a business attorney. Use legal_review for analysis. Flag critical legal risks.",
        tools=[legal_review],
    )

    tech_agent = client.as_agent(
        name="TechAdvisor",
        description="Technology expert.",
        instructions="You are a CTO-level tech advisor. Use tech_assessment for feasibility. Focus on practical solutions.",
        tools=[tech_assessment],
    )

    concierge = client.as_agent(
        name="Concierge",
        description="Routes questions to the right advisor.",
        instructions=(
            "You are the AI Advisory Board concierge. Understand the user's question and provide "
            "expert advice by leveraging your knowledge. Route complex questions:\n"
            "- Strategy & market → StrategyAdvisor\n"
            "- Finance & funding → FinanceAdvisor\n"
            "- Legal & compliance → LegalAdvisor\n"
            "- Technology & architecture → TechAdvisor\n\n"
            "Be welcoming and helpful."
        ),
        tools=[
            strategy_agent.as_tool(name="ask_strategy", description="Ask the strategy advisor"),
            finance_agent.as_tool(name="ask_finance", description="Ask the finance advisor"),
            legal_agent.as_tool(name="ask_legal", description="Ask the legal advisor"),
            tech_agent.as_tool(name="ask_tech", description="Ask the technology advisor"),
        ],
    )

    return concierge


agent = create_advisory_agent()
add_agent_framework_fastapi_endpoint(app, agent, path="/api/copilotkit")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "AI Advisory Board"}
