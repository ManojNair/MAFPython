# Lab 08 — Handoff Orchestration

## Objective

Build an interactive **customer support system** where agents dynamically transfer control to each other based on conversation context. You'll implement handoff routing, tool approval for sensitive operations, and autonomous mode.

---

## Concepts

### Handoff Orchestration Pattern

```
┌──────────┐       ┌──────────┐       ┌──────────┐
│  Triage  │──────►│ Billing  │──────►│ Returns  │
│  Agent   │◄──────│  Agent   │       │  Agent   │
└──────────┘       └──────────┘       └────┬─────┘
     │                                      │
     └─────────────►┌──────────┐◄──────────┘
                    │Technical │
                    │  Agent   │
                    └──────────┘

  ● Only ONE agent is active at a time
  ● Full context transfers with the handoff
  ● Agents decide WHEN to hand off based on conversation
```

**Key characteristics:**
- **Dynamic delegation** — agents decide at runtime which agent should handle the task next
- **One active agent** at a time — full control transfers (unlike agent-as-tool)
- **Full context preservation** — conversation history is shared across all handoffs
- **Interactive** — when an agent doesn't hand off, it asks the user for more input

**Also known as:** Routing, Triage, Transfer, Dispatch, Delegation

### Handoff vs Agent-as-Tool (revisited)

| Aspect | Handoff | Agent-as-Tool |
|--------|---------|--------------|
| Control | Full transfer | Returns to caller |
| Active agents | One at a time | Caller stays active |
| Context | Entire conversation | Only the query |
| User interaction | Agent talks directly to user | Caller talks to user |

---

## Setup

```bash
mkdir -p lab08 && cd lab08
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
Lab 08 — Handoff Orchestration
Microsoft Agent Framework Workshop

Demonstrates:
  - HandoffBuilder for dynamic agent-to-agent delegation
  - Interactive request/response loop
  - Custom handoff routing rules
  - Tool approval (HITL) for sensitive operations
  - Autonomous mode
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
        # Custom routing rules (optional — by default all can handoff to all)
        .add_handoff(triage_agent, [billing_agent, order_agent, returns_agent, tech_agent])
        .add_handoff(billing_agent, [triage_agent, returns_agent])
        .add_handoff(order_agent, [triage_agent, returns_agent])
        .add_handoff(returns_agent, [triage_agent, tech_agent])
        .add_handoff(tech_agent, [triage_agent, returns_agent])
        # Enable autonomous mode so agents continue without user input when possible
        .with_autonomous_mode(
            agents=[triage_agent],
            turn_limits={triage_agent.name: 3},
        )
        .build()
    )

    # ── Run the Interactive Workflow ──

    print("=" * 60)
    print("HANDOFF ORCHESTRATION: Customer Support System")
    print("=" * 60)
    print("(Type your messages to interact with the support agents)")
    print("(Type 'quit' to exit)")
    print("-" * 60)

    # Start the workflow with an initial customer message
    initial_message = (
        "Hi, I ordered a laptop (order ORD-1234) but it arrived with a cracked screen. "
        "I'd like to return it and get a refund."
    )

    print(f"\nCustomer: {initial_message}\n")

    pending_requests: list[WorkflowEvent] = []

    async for event in workflow.run(initial_message, stream=True):
        if event.type == "request_info" and isinstance(event.data, HandoffAgentUserRequest):
            pending_requests.append(event)
            for msg in event.data.agent_response.messages[-2:]:
                if msg.text:
                    print(f"[{msg.author_name or event.executor_id}]: {msg.text}")
        elif event.type == "request_info" and isinstance(event.data, Content) and event.data.type == "function_approval_request":
            # Tool approval request (HITL)
            pending_requests.append(event)
            func_call = event.data.function_call
            args = func_call.parse_arguments() or {}
            print(f"\n⚠️  APPROVAL REQUIRED: {func_call.name}")
            print(f"   Arguments: {args}")
        elif event.type == "output":
            print("\n✅ Workflow completed!")

    # Interactive loop
    max_turns = 5
    turn = 0
    while pending_requests and turn < max_turns:
        turn += 1

        responses: dict[str, object] = {}
        for req in pending_requests:
            if isinstance(req.data, HandoffAgentUserRequest):
                # Simulate user input for the demo
                user_inputs = [
                    "Yes, I'd like to return order ORD-1234 because the screen is cracked.",
                    "Yes please, process the full refund.",
                    "Thank you!",
                ]
                user_input = user_inputs[min(turn - 1, len(user_inputs) - 1)]
                print(f"\nCustomer: {user_input}")
                responses[req.request_id] = HandoffAgentUserRequest.create_response(user_input)
            elif isinstance(req.data, Content) and req.data.type == "function_approval_request":
                # Auto-approve for demo
                print("   ✅ Approved by supervisor")
                responses[req.request_id] = req.data.to_function_approval_response(approved=True)

        pending_requests = []
        async for event in workflow.run(responses=responses, stream=True):
            if event.type == "request_info" and isinstance(event.data, HandoffAgentUserRequest):
                pending_requests.append(event)
                for msg in event.data.agent_response.messages[-2:]:
                    if msg.text:
                        print(f"[{msg.author_name or event.executor_id}]: {msg.text}")
            elif event.type == "request_info" and isinstance(event.data, Content) and event.data.type == "function_approval_request":
                pending_requests.append(event)
                func_call = event.data.function_call
                args = func_call.parse_arguments() or {}
                print(f"\n⚠️  APPROVAL REQUIRED: {func_call.name}")
                print(f"   Arguments: {args}")
            elif event.type == "output":
                print("\n✅ Workflow completed!")

    print("\n" + "=" * 60)
    print("Session ended.")
    print("=" * 60)


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
HANDOFF ORCHESTRATION: Customer Support System
============================================================
(Type your messages to interact with the support agents)
(Type 'quit' to exit)
------------------------------------------------------------

Customer: Hi, I ordered a laptop (order ORD-1234) but it arrived with
a cracked screen. I'd like to return it and get a refund.

[triage_agent]: I'm sorry to hear about the damaged laptop. Let me
connect you with our returns specialist who can help with that.

[returns_agent]: I'm sorry about the cracked screen. Let me help you
with the return and refund. Could you confirm you'd like to proceed?

Customer: Yes, I'd like to return order ORD-1234 because the screen is cracked.

[returns_agent]: I've initiated the return for ORD-1234. A return label
has been sent to your email. Now let me process your refund...

⚠️  APPROVAL REQUIRED: process_refund
   Arguments: {'order_number': 'ORD-1234', 'amount': 150.0}
   ✅ Approved by supervisor

[returns_agent]: Your refund of $150.00 has been approved and processed.
Expect it within 5-7 business days.

Customer: Thank you!

✅ Workflow completed!

============================================================
Session ended.
============================================================
```

---

## Key Takeaways

1. **`HandoffBuilder`** creates workflows where agents dynamically transfer control to each other.
2. **`.with_start_agent()`** defines which agent receives the initial user input.
3. **`.add_handoff(from, [to_list])`** configures specific routing rules between agents.
4. **Interactive loop**: When an agent doesn't hand off, it emits a `HandoffAgentUserRequest` — you must provide user input to continue.
5. **`@tool(approval_mode="always_require")`** creates HITL gates — sensitive operations require human approval before execution.
6. **`.with_autonomous_mode()`** lets specified agents continue without user input.
7. Full conversation context is **broadcast to all agents** after each turn.

---

## What's Next?

In **[Lab 09 — Group Chat Orchestration](lab-09-group-chat-orchestration.md)**, you'll build a collaborative debate system where multiple agents discuss and refine ideas in a shared conversation thread.
