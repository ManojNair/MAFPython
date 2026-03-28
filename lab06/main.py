"""
Lab 06 — Sequential Orchestration
Microsoft Agent Framework Workshop

Demonstrates:
  - SequentialBuilder for pipeline workflows
  - Blog post creation: Researcher → Writer → Editor → SEO Optimizer
  - Streaming workflow events
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

    # Build the sequential pipeline
    workflow = SequentialBuilder(
        participants=[researcher, writer, editor, seo_optimizer]
    ).build()

    topic = (
        "Write a blog post about how AI agents are transforming software development "
        "in 2026, focusing on multi-agent orchestration patterns."
    )

    print("=" * 60)
    print("SEQUENTIAL ORCHESTRATION: Blog Post Pipeline")
    print("=" * 60)
    print(f"\nTopic: {topic}\n")
    print("-" * 60)

    outputs: list[list[Message]] = []
    async for event in workflow.run(topic, stream=True):
        if event.type == "output":
            outputs.append(cast(list[Message], event.data))

    if outputs:
        final_conversation = outputs[-1]
        for msg in final_conversation:
            name = msg.author_name or ("user" if msg.role == "user" else "assistant")
            print(f"\n{'='*60}")
            print(f"[{name}]")
            print(f"{'='*60}")
            print(msg.text)


if __name__ == "__main__":
    asyncio.run(main())
