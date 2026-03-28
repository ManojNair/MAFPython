"""
Lab 01 — Your First Agent
Microsoft Agent Framework Workshop

Demonstrates:
  - Creating an AzureOpenAIResponsesClient with DefaultAzureCredential
  - Building an agent with name and instructions
  - Running the agent (non-streaming)
  - Running the agent (streaming)
"""

import asyncio
import os

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework.azure import AzureOpenAIResponsesClient

load_dotenv()


async def main():
    # Step 1: Create the Chat Client
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    # Step 2: Create an Agent
    agent = client.as_agent(
        name="HelloAgent",
        instructions=(
            "You are a friendly and knowledgeable assistant. "
            "Keep your answers concise — aim for 2-3 sentences. "
            "If you don't know something, say so honestly."
        ),
    )

    # Step 3: Non-Streaming Run
    print("=" * 60)
    print("NON-STREAMING RESPONSE")
    print("=" * 60)

    result = await agent.run("What is the capital of France?")
    print(f"Agent: {result}\n")
    print(f"Response text: {result.text}")
    print(f"Number of messages: {len(result.messages)}")

    # Step 4: Streaming Run
    print("\n" + "=" * 60)
    print("STREAMING RESPONSE")
    print("=" * 60)
    print("Agent: ", end="", flush=True)

    async for chunk in agent.run(
        "Explain quantum computing in simple terms.", stream=True
    ):
        if chunk.text:
            print(chunk.text, end="", flush=True)

    print("\n")

    # Step 5: Multiple Independent Questions
    print("=" * 60)
    print("MULTIPLE INDEPENDENT QUESTIONS")
    print("=" * 60)

    questions = [
        "What's the largest ocean on Earth?",
        "Who painted the Mona Lisa?",
        "What is 42 * 17?",
    ]

    for question in questions:
        result = await agent.run(question)
        print(f"Q: {question}")
        print(f"A: {result}\n")


if __name__ == "__main__":
    asyncio.run(main())
