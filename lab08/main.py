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


@tool
def check_order_status(order_number: Annotated[str, Field(description="Order number")]) -> str:
    """Check the status of an order."""
    statuses = {
        "ORD-1234": "Shipped — arriving March 30, 2026",
        "ORD-5678": "Processing — expected to ship tomorrow",
        "ORD-9999": "Delivered on March 25, 2026",
    }
    return statuses.get(order_number, f"Order {order_number} not found.")


@tool
def check_billing(account_id: Annotated[str, Field(description="Account ID")]) -> str:
    """Check billing information."""
    return f"Account {account_id}: Balance $0.00, Last payment $150.00, Next bill $75.00 due April 1."


@tool(approval_mode="always_require")
def process_refund(
    order_number: Annotated[str, Field(description="Order number")],
    amount: Annotated[float, Field(description="Refund amount in USD")],
) -> str:
    """Process a refund. Requires human approval."""
    return f"Refund of ${amount:.2f} processed for {order_number}. Expect 5-7 business days."


@tool
def initiate_return(
    order_number: Annotated[str, Field(description="Order number")],
    reason: Annotated[str, Field(description="Reason for return")],
) -> str:
    """Initiate a product return."""
    return f"Return initiated for {order_number} (reason: {reason}). Return label sent to email."


@tool
def run_diagnostics(issue_type: Annotated[str, Field(description="Issue type")]) -> str:
    """Run technical diagnostics."""
    return f"Diagnostics for '{issue_type}': No outages detected. Try: clear cache, restart, check network."


async def main():
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    triage_agent = client.as_agent(
        name="triage_agent",
        description="Frontline support — routes to specialists.",
        instructions=(
            "You are frontline customer support triage. Route to:\n"
            "- billing_agent for billing issues\n"
            "- order_agent for order/shipping issues\n"
            "- returns_agent for returns/refunds\n"
            "- tech_agent for technical problems\n"
            "Be polite and professional."
        ),
    )

    billing_agent = client.as_agent(
        name="billing_agent",
        description="Handles billing inquiries.",
        instructions="You handle billing inquiries. Use check_billing to look up accounts. "
                     "For refunds, hand off to returns_agent.",
        tools=[check_billing],
    )

    order_agent = client.as_agent(
        name="order_agent",
        description="Handles order tracking.",
        instructions="You handle order inquiries. Use check_order_status to look up orders. "
                     "For returns, hand off to returns_agent.",
        tools=[check_order_status],
    )

    returns_agent = client.as_agent(
        name="returns_agent",
        description="Handles returns and refunds.",
        instructions="You manage returns and refunds. Use initiate_return for returns, "
                     "process_refund for refunds (requires supervisor approval).",
        tools=[initiate_return, process_refund],
    )

    tech_agent = client.as_agent(
        name="tech_agent",
        description="Handles technical support.",
        instructions="You handle technical issues. Use run_diagnostics. "
                     "For refunds, hand off to returns_agent.",
        tools=[run_diagnostics],
    )

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
        .with_autonomous_mode(agents=[triage_agent], turn_limits={triage_agent.name: 3})
        .build()
    )

    print("=" * 60)
    print("HANDOFF ORCHESTRATION: Customer Support System")
    print("=" * 60)

    initial_message = (
        "Hi, I ordered a laptop (order ORD-1234) but it arrived with a cracked screen. "
        "I'd like to return it and get a refund."
    )
    print(f"\nCustomer: {initial_message}\n")

    pending_requests: list[WorkflowEvent] = []

    async for event in workflow.run_stream(initial_message):
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

    # Interactive loop (simulated for demo)
    user_inputs = [
        "Yes, I'd like to return order ORD-1234 because the screen is cracked.",
        "Yes please, process the full refund.",
        "Thank you!",
    ]
    max_turns = 5
    turn = 0

    while pending_requests and turn < max_turns:
        responses: dict[str, object] = {}
        for req in pending_requests:
            if isinstance(req.data, HandoffAgentUserRequest):
                user_input = user_inputs[min(turn, len(user_inputs) - 1)]
                print(f"\nCustomer: {user_input}")
                responses[req.request_id] = HandoffAgentUserRequest.create_response(user_input)
            elif isinstance(req.data, Content) and req.data.type == "function_approval_request":
                print("   ✅ Approved by supervisor")
                responses[req.request_id] = req.data.to_function_approval_response(approved=True)
        turn += 1

        pending_requests = []
        async for event in workflow.run(responses=responses):
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


if __name__ == "__main__":
    asyncio.run(main())
