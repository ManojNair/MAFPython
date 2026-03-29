# Lab 11 — Multi-Agent Web App with CopilotKit

## Objective

Build a production-ready **web application** with a beautiful chat interface that showcases multi-agent orchestration. You'll use **AG-UI** (Agent-to-UI protocol) for the backend and **CopilotKit** for the frontend — the officially recommended stack for Agent Framework web apps.

---

## Concepts

### Architecture

```
┌────────────────────────┐         ┌────────────────────────────┐
│    Frontend (Next.js)  │  SSE    │     Backend (FastAPI)      │
│                        │◄───────►│                            │
│  CopilotKit Components │  HTTP   │  agent-framework-ag-ui     │
│  - <CopilotChat />     │         │  - AgentFrameworkAgent     │
│  - Streaming messages   │         │  - Handoff workflow        │
│  - Agent avatars        │         │  - Function tools          │
│  - Tool call rendering  │         │  - Azure OpenAI            │
└────────────────────────┘         └────────────────────────────┘
        Port 3000                          Port 8000
```

### What is AG-UI?

AG-UI is a standardized protocol for building AI agent web interfaces:
- **Server-Sent Events (SSE)** for real-time streaming
- **Standardized message format** for reliable agent interactions
- **Built-in HITL support** for approval workflows
- **State synchronization** between client and server

### What is CopilotKit?

CopilotKit provides polished React components that implement the AG-UI protocol:
- `<CopilotChat />` — Beautiful chat bubbles with streaming
- Agent identification and avatars
- Tool call visualization
- Approval buttons for HITL

---

## Setup

### Backend Setup

```bash
mkdir -p lab11 && cd lab11
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### `requirements.txt`

```txt
agent-framework --pre
agent-framework-ag-ui --pre
azure-identity
python-dotenv
fastapi
uvicorn[standard]
```

### `.env` (in lab11/)

```env
AZURE_OPENAI_ENDPOINT=https://letsaifoundryprj-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5.2
```

### Frontend Setup

```bash
cd lab11
npx create-next-app@latest frontend --typescript --tailwind --app --use-npm --eslint
cd frontend
npm install @copilotkit/react-core @copilotkit/react-ui
```

---

## Backend Code

Create `lab11/server.py`:

```python
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


# CopilotKit sends an RPC envelope; this middleware unwraps it for AG-UI
from starlette.middleware.base import BaseHTTPMiddleware


class CopilotKitUnwrapMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path == "/api/copilotkit":
            body_bytes = await request.body()
            try:
                data = json.loads(body_bytes)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return await call_next(request)
            if "body" in data and "method" in data:
                data = data["body"]
            data = _convert_keys(data)
            new_body = json.dumps(data).encode()

            async def receive():
                return {"type": "http.request", "body": new_body}

            request._receive = receive
        return await call_next(request)


app.add_middleware(CopilotKitUnwrapMiddleware)

add_agent_framework_fastapi_endpoint(app, agent, path="/api/copilotkit")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "AI Advisory Board"}
```

---

## Frontend Code

### `lab11/frontend/src/app/layout.tsx`

```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI Advisory Board",
  description: "Multi-Agent Business Advisory powered by Microsoft Agent Framework",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
```

### `lab11/frontend/src/app/page.tsx`

```tsx
"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      {/* Header */}
      <header className="border-b border-white/10 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <span className="text-white text-xl">🤖</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">AI Advisory Board</h1>
              <p className="text-xs text-blue-300">
                Powered by Microsoft Agent Framework
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
              ● Connected
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 py-8">
        {/* Info Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          {[
            { emoji: "📊", title: "Strategy", desc: "Market & growth" },
            { emoji: "💰", title: "Finance", desc: "ROI & funding" },
            { emoji: "⚖️", title: "Legal", desc: "Compliance & IP" },
            { emoji: "🔧", title: "Tech", desc: "Architecture" },
          ].map((card) => (
            <div
              key={card.title}
              className="p-4 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm text-center"
            >
              <span className="text-2xl">{card.emoji}</span>
              <h3 className="text-sm font-semibold text-white mt-2">
                {card.title}
              </h3>
              <p className="text-xs text-blue-300">{card.desc}</p>
            </div>
          ))}
        </div>

        {/* Chat */}
        <div className="rounded-2xl overflow-hidden border border-white/10 shadow-2xl h-[600px]">
          <CopilotKit
            runtimeUrl="http://localhost:8000/api/copilotkit"
          >
            <CopilotChat
              labels={{
                title: "AI Advisory Board",
                initial: "👋 Welcome! I'm your AI Advisory Board concierge. Ask me any business question — I'll connect you with our Strategy, Finance, Legal, or Tech advisors.\n\nTry asking:\n• \"I want to start an AI startup — what should I know?\"\n• \"What's the market size for healthtech?\"\n• \"Help me plan the tech architecture for a SaaS platform\"",
              }}
              className="h-full"
            />
          </CopilotKit>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-blue-400/50 mt-6">
          Built with Microsoft Agent Framework · AG-UI Protocol · CopilotKit
        </p>
      </main>
    </div>
  );
}
```

---

## Running the Application

### 1. Start the Backend

```bash
cd lab11
source .venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Verify: `curl http://localhost:8000/health` → `{"status": "healthy", ...}`

### 2. Start the Frontend

```bash
cd lab11/frontend
npm run dev
```

### 3. Open the App

Navigate to `http://localhost:3000` in your browser.

### Try These Prompts

1. **"I want to build an AI-powered tutoring platform"** — Routes to Strategy for market analysis
2. **"What's the ROI for a fintech startup?"** — Routes to Finance for financial modeling
3. **"What legal considerations for a health data startup?"** — Routes to Legal
4. **"Design a microservices architecture for an e-commerce AI platform"** — Routes to Tech

---

## Key Takeaways

1. **AG-UI protocol** provides standardized real-time streaming between agents and web clients via SSE.
2. **`agent-framework-ag-ui`** + FastAPI = production-ready backend with one line: `add_agent_framework_fastapi_endpoint(app, agent, path=...)`.
3. **CopilotKit** provides beautiful, ready-made React components for agent chat interfaces.
4. The same agent and workflow code from previous labs works unchanged — AG-UI just adds a web-friendly transport layer.
5. The architecture cleanly separates concerns: **backend** (agent logic) ↔ **AG-UI** (protocol) ↔ **frontend** (UI).

---

## What's Next?

In **[Lab 12 — Deploy to Azure](lab-12-deploy-to-azure.md)**, you'll deploy this web app to **Azure Container Apps** — making it publicly accessible with managed identity for secure authentication.
