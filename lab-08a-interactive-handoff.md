# Lab 08a — Interactive Handoff Orchestration

## Objective

Build a **fully interactive** version of the customer support handoff system. Instead of hardcoded prompts, you'll type messages in the console and watch agents hand off control to each other in real time — with clear visual banners marking each handoff.

---

## What's Different from Lab 08?

| Aspect | Lab 08 | Lab 08a |
|--------|--------|---------|
| User input | Hardcoded messages | Interactive `input()` prompts |
| Conversation length | Fixed (5 turns max) | Unlimited (until you type `quit`) |
| Handoff visibility | Implicit (agent name in brackets) | Explicit banners showing `from → to` |
| Tool approvals | Auto-approved | User confirms `yes/no` in console |

---

## Concepts

### Visualizing Handoffs

When an agent hands off to another, you'll see a clear banner:

```
+----------------------------------------------------------+
|  HANDOFF: triage_agent --> returns_agent                  |
+----------------------------------------------------------+
```

This makes it easy to see the delegation chain as you interact with the system.

### Interactive Flow

```
You type a message
       │
       ▼
┌──────────┐
│  Triage  │ ◄── always starts here
│  Agent   │
└────┬─────┘
     │  decides who should handle it
     ▼
+----------------------------------------------------------+
|  HANDOFF: triage_agent --> returns_agent                  |
+----------------------------------------------------------+
     │
┌────▼─────┐
│ Returns  │ ◄── takes over, talks to you directly
│  Agent   │
└────┬─────┘
     │  needs refund approval
     ▼
  APPROVAL REQUIRED: process_refund
  Approve? (yes/no): ◄── you decide
```

---

## Setup

```bash
mkdir -p lab08a && cd lab08a
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
Lab 08a — Interactive Handoff Orchestration
Microsoft Agent Framework Workshop

Demonstrates:
  - Fully interactive console-based handoff workflow
  - Clear visual demarcation of agent handoffs
  - Real user input at each turn (no hardcoded prompts)
  - Tool approval (HITL) with user confirmation
  - Handoff tracking to show which agent is currently active
"""

import asyncio
import os
from typing import Annotated

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pydantic import Field

from agent_framework import Content, WorkflowEvent, tool
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework.orchestrations import HandoffBuilder, HandoffAgentUserRequest

load_dotenv()


# ── Tool Definitions ──

@tool
def check_order_status(
    order_number: Annotated[str, Field(description="Order number to check")],
) -> str:
    """Check the status of a given order number."""
    statuses = {
        "ORD-1234": "Shipped — arriving March 30, 2026",
        "ORD-5678": "Processing — expected to ship tomorrow",
        "ORD-9999": "Delivered on March 25, 2026",
    }
    return statuses.get(order_number, f"Order {order_number} not found in our system.")


@tool
def check_billing(
    account_id: Annotated[str, Field(description="Customer account ID")],
) -> str:
    """Check billing information for a customer account."""
    return (
        f"Account {account_id}: Current balance $0.00, "
        f"Last payment $150.00 on March 15, 2026. "
        f"Next bill: $75.00 due April 1, 2026."
    )


@tool(approval_mode="always_require")
def process_refund(
    order_number: Annotated[str, Field(description="Order number to refund")],
    amount: Annotated[float, Field(description="Refund amount in USD")],
) -> str:
    """Process a refund for a given order. Requires human approval."""
    return f"Refund of ${amount:.2f} processed for order {order_number}. Expect 5-7 business days."


@tool
def initiate_return(
    order_number: Annotated[str, Field(description="Order number to return")],
    reason: Annotated[str, Field(description="Reason for return")],
) -> str:
    """Initiate a product return for a given order."""
    return (
        f"Return initiated for {order_number} (reason: {reason}). "
        f"Return label sent to email. Ship within 14 days."
    )


@tool
def run_diagnostics(
    issue_type: Annotated[str, Field(description="Type of technical issue")],
) -> str:
    """Run technical diagnostics for a reported issue."""
    return (
        f"Diagnostics for '{issue_type}': "
        f"No outages detected. Recommended: clear cache, restart device, "
        f"check network connectivity. If issue persists, escalate to Tier 2."
    )


# ── Handoff Display Helper ──

def print_handoff_banner(from_agent: str | None, to_agent: str):
    """Print a clear visual banner when a handoff occurs."""
    print()
    print("+" + "-" * 58 + "+")
    if from_agent:
        print(f"|  HANDOFF: {from_agent} --> {to_agent}".ljust(59) + "|")
    else:
        print(f"|  STARTING AGENT: {to_agent}".ljust(59) + "|")
    print("+" + "-" * 58 + "+")
    print()


def process_events(event: WorkflowEvent, current_agent: str | None) -> str | None:
    """Process a workflow event, print output, and track the active agent.

    Returns the updated current_agent name.
    """
    # Detect agent handoffs via executor_id changes
    if event.executor_id and event.executor_id != current_agent:
        print_handoff_banner(current_agent, event.executor_id)
        current_agent = event.executor_id

    if event.type == "request_info" and isinstance(event.data, HandoffAgentUserRequest):
        for msg in event.data.agent_response.messages[-2:]:
            if msg.text:
                print(f"  [{msg.author_name or event.executor_id}]: {msg.text}")
    elif event.type == "output":
        print("\n  Workflow completed for this turn.")

    return current_agent


async def main():
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    # ── Define Specialized Agents ──

    triage_agent = client.as_agent(
        name="triage_agent",
        description="Frontline support — handles general inquiries and routes to specialists.",
        instructions=(
            "You are the frontline customer support triage agent. "
            "Greet the customer, understand their issue, and route to the appropriate specialist:\n"
            "- Billing issues → hand off to billing_agent\n"
            "- Order/shipping issues → hand off to order_agent\n"
            "- Returns/refunds → hand off to returns_agent\n"
            "- Technical problems → hand off to tech_agent\n\n"
            "If you can answer a simple question directly, do so. "
            "Always be polite and professional."
        ),
    )

    billing_agent = client.as_agent(
        name="billing_agent",
        description="Handles billing inquiries, payment issues, and account charges.",
        instructions=(
            "You handle billing and payment inquiries. Use the check_billing tool "
            "to look up account information. Be helpful and clear about charges. "
            "If the customer wants a refund, hand off to returns_agent."
        ),
        tools=[check_billing],
    )

    order_agent = client.as_agent(
        name="order_agent",
        description="Handles order tracking and shipping issues.",
        instructions=(
            "You handle order and shipping inquiries. Use check_order_status "
            "to look up orders. If the customer wants to return an item, "
            "hand off to returns_agent."
        ),
        tools=[check_order_status],
    )

    returns_agent = client.as_agent(
        name="returns_agent",
        description="Handles product returns and refund processing.",
        instructions=(
            "You manage returns and refunds. Use initiate_return for returns "
            "and process_refund for refunds. The refund tool requires approval "
            "from a supervisor — explain this to the customer. "
            "If the issue is technical, hand off to tech_agent."
        ),
        tools=[initiate_return, process_refund],
    )

    tech_agent = client.as_agent(
        name="tech_agent",
        description="Handles technical support and troubleshooting.",
        instructions=(
            "You handle technical issues. Use run_diagnostics to troubleshoot. "
            "If the customer needs a refund due to a technical issue, "
            "hand off to returns_agent."
        ),
        tools=[run_diagnostics],
    )

    # ── Build the Handoff Workflow ──

    workflow = (
        HandoffBuilder(
            name="customer_support",
            participants=[triage_agent, billing_agent, order_agent, returns_agent, tech_agent],
        )
        .with_start_agent(triage_agent)
        .add_handoff(triage_agent, [billing_agent, order_agent, returns_agent, tech_agent])
        .add_handoff(billing_agent, [triage_agent, returns_agent])
        .add_handoff(order_agent, [triage_agent, returns_agent])
        .add_handoff(returns_agent, [triage_agent, tech_agent])
        .add_handoff(tech_agent, [triage_agent, returns_agent])
        .with_autonomous_mode(
            agents=[triage_agent],
            turn_limits={triage_agent.name: 3},
        )
        .build()
    )

    # ── Interactive Console Loop ──

    print("=" * 60)
    print("  INTERACTIVE HANDOFF DEMO: Customer Support System")
    print("=" * 60)
    print("  Type your message to talk to the support agents.")
    print("  Type 'quit' to exit.")
    print("=" * 60)

    # Get the first message from the user
    user_input = input("\nYou: ").strip()
    if not user_input or user_input.lower() == "quit":
        print("Goodbye!")
        return

    current_agent: str | None = None
    pending_requests: list[WorkflowEvent] = []

    # Initial run
    async for event in workflow.run(user_input, stream=True):
        current_agent = process_events(event, current_agent)

        if event.type == "request_info" and isinstance(event.data, HandoffAgentUserRequest):
            pending_requests.append(event)
        elif event.type == "request_info" and isinstance(event.data, Content) and event.data.type == "function_approval_request":
            pending_requests.append(event)
            func_call = event.data.function_call
            args = func_call.parse_arguments() or {}
            print(f"\n  APPROVAL REQUIRED: {func_call.name}")
            print(f"  Arguments: {args}")

    # Continue until user quits or workflow ends
    while pending_requests:
        responses: dict[str, object] = {}

        for req in pending_requests:
            if isinstance(req.data, HandoffAgentUserRequest):
                # Get real input from the user
                user_input = input("\nYou: ").strip()
                if user_input.lower() == "quit":
                    print("\n" + "=" * 60)
                    print("  Session ended by user.")
                    print("=" * 60)
                    return
                responses[req.request_id] = HandoffAgentUserRequest.create_response(user_input)

            elif isinstance(req.data, Content) and req.data.type == "function_approval_request":
                # Ask user for approval
                approval = input("  Approve? (yes/no): ").strip().lower()
                approved = approval in ("yes", "y")
                print(f"  {'Approved' if approved else 'Denied'}")
                responses[req.request_id] = req.data.to_function_approval_response(approved=approved)

        pending_requests = []

        async for event in workflow.run(responses=responses, stream=True):
            current_agent = process_events(event, current_agent)

            if event.type == "request_info" and isinstance(event.data, HandoffAgentUserRequest):
                pending_requests.append(event)
            elif event.type == "request_info" and isinstance(event.data, Content) and event.data.type == "function_approval_request":
                pending_requests.append(event)
                func_call = event.data.function_call
                args = func_call.parse_arguments() or {}
                print(f"\n  APPROVAL REQUIRED: {func_call.name}")
                print(f"  Arguments: {args}")

    print("\n" + "=" * 60)
    print("  Session ended.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Run It

```bash
python main.py
```

### Example Session

```
============================================================
  INTERACTIVE HANDOFF DEMO: Customer Support System
============================================================
  Type your message to talk to the support agents.
  Type 'quit' to exit.
============================================================

You: Hi, I ordered a laptop (order ORD-1234) but it has a cracked screen.

+----------------------------------------------------------+
|  STARTING AGENT: triage_agent                            |
+----------------------------------------------------------+

  [triage_agent]: I'm sorry to hear about the damaged laptop.
  Let me connect you with our returns specialist.

+----------------------------------------------------------+
|  HANDOFF: triage_agent --> returns_agent                  |
+----------------------------------------------------------+

  [returns_agent]: I'm sorry about the cracked screen on your laptop.
  I can help you with a return and refund. Would you like me to
  initiate a return for order ORD-1234?

You: Yes please, and I'd like a full refund.

  [returns_agent]: I've initiated the return. A return label has been
  sent to your email. Now let me process the refund...

  APPROVAL REQUIRED: process_refund
  Arguments: {'order_number': 'ORD-1234', 'amount': 150.0}
  Approve? (yes/no): yes
  Approved

  [returns_agent]: Your refund of $150.00 has been approved and processed.
  You should see it within 5-7 business days.

You: Thanks! I also have a question about my internet bill for account ACC-001.

+----------------------------------------------------------+
|  HANDOFF: returns_agent --> triage_agent                  |
+----------------------------------------------------------+

+----------------------------------------------------------+
|  HANDOFF: triage_agent --> billing_agent                  |
+----------------------------------------------------------+

  [billing_agent]: I've looked up account ACC-001. Your current balance
  is $0.00, with a last payment of $150.00 on March 15. Your next bill
  of $75.00 is due April 1, 2026.

You: quit

============================================================
  Session ended by user.
============================================================
```

---

## Key Takeaways

1. **Interactive input** — `input()` prompts replace hardcoded messages, letting you steer the conversation naturally.
2. **Handoff banners** — tracking `event.executor_id` changes lets you clearly show when control transfers between agents.
3. **User-controlled approvals** — sensitive operations like refunds require explicit `yes/no` confirmation instead of auto-approval.
4. **Open-ended conversation** — the loop continues until the user types `quit` or the workflow has no more pending requests.
5. **Same workflow, different UX** — the underlying `HandoffBuilder` setup is identical to Lab 08; only the interaction layer changed.

---

## Try These Scenarios

- **Multi-hop handoff**: Start with a billing question, then ask about an order, then request a return — watch the handoff chain.
- **Deny a refund**: When the approval prompt appears, type `no` and see how the agent responds.
- **Technical escalation**: Report a technical issue and watch it route through `tech_agent`, then ask for a refund to trigger a handoff to `returns_agent`.

---

## What's Next?

Continue to **[Lab 09 — Group Chat Orchestration](lab-09-group-chat-orchestration.md)** to see how multiple agents can collaborate simultaneously in a shared conversation.
