"""
Lab 11 — Multi-Agent Web App Backend
Microsoft Agent Framework Workshop

AG-UI + FastAPI server that exposes a multi-agent handoff workflow
as an HTTP endpoint with Server-Sent Events streaming.
"""

import json
import os
import re
from typing import Annotated

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import Field

from agent_framework import tool
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework_ag_ui import add_agent_framework_fastapi_endpoint

load_dotenv()

app = FastAPI(title="AI Advisory Board", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Tool Definitions ──

@tool(description="Analyze market size and growth potential for a business idea.")
def analyze_market(
    industry: Annotated[str, Field(description="Industry or market segment to analyze")],
) -> str:
    """Analyze market opportunity."""
    markets = {
        "ai": "Global AI market: $500B (2026), CAGR 37%. Key segments: Enterprise AI, GenAI, AI Agents.",
        "fintech": "Global fintech market: $310B (2026), CAGR 25%. Key segments: Digital payments, neobanks, DeFi.",
        "healthtech": "Global healthtech market: $450B (2026), CAGR 22%. Key segments: Telehealth, AI diagnostics, wearables.",
        "edtech": "Global edtech market: $200B (2026), CAGR 18%. Key segments: Online learning, AI tutoring, VR/AR.",
    }
    return markets.get(industry.lower(), f"Market data for {industry}: Estimated $50-100B, growing 15-20% annually.")


@tool(description="Perform financial modeling and ROI analysis.")
def financial_analysis(
    scenario: Annotated[str, Field(description="Business scenario to analyze financially")],
) -> str:
    """Run financial analysis."""
    return (
        f"Financial Analysis for '{scenario}':\n"
        f"- Initial investment: $500K-2M estimated\n"
        f"- Break-even: 18-24 months\n"
        f"- Projected Year 1 revenue: $1-3M\n"
        f"- Projected Year 3 revenue: $10-25M\n"
        f"- IRR: 35-45%\n"
        f"- Key risk: Market timing and competitive entry"
    )


@tool(description="Review legal and regulatory considerations for a business.")
def legal_review(
    business_type: Annotated[str, Field(description="Type of business for legal review")],
) -> str:
    """Review legal considerations."""
    return (
        f"Legal Review for '{business_type}':\n"
        f"- Entity structure: Recommend Delaware C-Corp for VC funding\n"
        f"- IP protection: File provisional patents early, register trademarks\n"
        f"- Compliance: GDPR, SOC2, industry-specific regulations\n"
        f"- Contracts: Standard SaaS terms, DPA for data processing\n"
        f"- Employment: Equity vesting, non-compete considerations"
    )


@tool(description="Assess technical feasibility and architecture recommendations.")
def tech_assessment(
    project: Annotated[str, Field(description="Technical project or product to assess")],
) -> str:
    """Assess technical feasibility."""
    return (
        f"Technical Assessment for '{project}':\n"
        f"- Architecture: Microservices on Azure Container Apps\n"
        f"- AI/ML: Azure OpenAI + Agent Framework for multi-agent orchestration\n"
        f"- Data: Azure Cosmos DB for operational, Azure Data Lake for analytics\n"
        f"- Timeline: MVP in 3-4 months, production in 6-8 months\n"
        f"- Team: 3-4 engineers, 1 ML engineer, 1 designer\n"
        f"- Tech risk: Low — proven tech stack, good Azure integration"
    )


# ── Agent Setup ──

def create_advisory_agent():
    """Create the multi-agent advisory board."""
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    # Strategy advisor
    strategy_agent = client.as_agent(
        name="StrategyAdvisor",
        description="Business strategy expert — market analysis and go-to-market planning.",
        instructions=(
            "You are a seasoned business strategy advisor. Analyze business ideas, "
            "market opportunities, and competitive landscapes. Use the analyze_market "
            "tool for data-driven insights. Provide actionable strategic recommendations. "
            "Be concise and impactful."
        ),
        tools=[analyze_market],
    )

    # Finance advisor
    finance_agent = client.as_agent(
        name="FinanceAdvisor",
        description="Financial expert — ROI analysis, funding strategy, and financial modeling.",
        instructions=(
            "You are a financial advisor specializing in startups and growth companies. "
            "Use financial_analysis for quantitative modeling. Advise on funding strategy, "
            "unit economics, and financial planning. Be specific with numbers."
        ),
        tools=[financial_analysis],
    )

    # Legal advisor
    legal_agent = client.as_agent(
        name="LegalAdvisor",
        description="Legal expert — regulatory compliance, IP protection, and corporate law.",
        instructions=(
            "You are a business attorney. Use legal_review for comprehensive analysis. "
            "Advise on entity structure, IP protection, compliance requirements, and "
            "contractual best practices. Flag critical legal risks."
        ),
        tools=[legal_review],
    )

    # Tech advisor
    tech_agent = client.as_agent(
        name="TechAdvisor",
        description="Technology expert — architecture, feasibility, and technical strategy.",
        instructions=(
            "You are a CTO-level technology advisor. Use tech_assessment for feasibility "
            "analysis. Recommend architecture, tech stack, team composition, and timeline. "
            "Focus on practical, scalable solutions."
        ),
        tools=[tech_assessment],
    )

    # Concierge/triage agent
    concierge = client.as_agent(
        name="Concierge",
        description="Routes business questions to the right advisor on the board.",
        instructions=(
            "You are the AI Advisory Board concierge. Welcome the user and understand "
            "their business question. Route to the right specialist:\n"
            "- Business strategy & market → StrategyAdvisor\n"
            "- Financial planning & funding → FinanceAdvisor\n"
            "- Legal & compliance → LegalAdvisor\n"
            "- Technology & architecture → TechAdvisor\n\n"
            "If the question spans multiple areas, start with the most relevant advisor."
        ),
    )

    return concierge


# ── Register endpoints ──

agent = create_advisory_agent()


def _camel_to_snake(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name).lower()


def _convert_keys(obj):
    if isinstance(obj, dict):
        return {_camel_to_snake(k): _convert_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_keys(item) for item in obj]
    return obj


@app.post("/api/copilotkit/info")
async def copilotkit_info():
    """CopilotKit runtime info — returns available agents."""
    return {
        "agents": [
            {
                "name": "default",
                "id": "default",
                "description": "AI Advisory Board — routes to Strategy, Finance, Legal, and Tech advisors.",
            }
        ],
        "actions": [],
    }


# Register the AG-UI agent endpoint
# CopilotKit calls POST /api/copilotkit with an RPC envelope, so we use
# middleware to unwrap it before the AG-UI handler sees it.
from starlette.middleware.base import BaseHTTPMiddleware


class CopilotKitUnwrapMiddleware(BaseHTTPMiddleware):
    """Unwrap CopilotKit's RPC envelope for the AG-UI endpoint."""

    async def dispatch(self, request: Request, call_next):
        if (
            request.method == "POST"
            and request.url.path == "/api/copilotkit"
        ):
            body_bytes = await request.body()
            try:
                data = json.loads(body_bytes)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return await call_next(request)

            # CopilotKit sends: {method: "agent/run", params: {...}, body: {...}}
            # AG-UI expects the body contents directly with snake_case keys
            if "body" in data and "method" in data:
                data = data["body"]

            data = _convert_keys(data)
            new_body = json.dumps(data).encode()

            async def receive():
                return {"type": "http.request", "body": new_body}

            request._receive = receive

        return await call_next(request)


app.add_middleware(CopilotKitUnwrapMiddleware)

# This registers POST /api/copilotkit which receives the unwrapped AG-UI request
add_agent_framework_fastapi_endpoint(app, agent, path="/api/copilotkit")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "AI Advisory Board"}
