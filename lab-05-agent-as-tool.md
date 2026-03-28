# Lab 05 — Agent as Tool

## Objective

Learn to **compose agents** by using one agent as a tool for another. You'll build a concierge agent that delegates specialized tasks to sub-agents — a weather expert and a restaurant recommender — creating a hierarchical agent system.

---

## Concepts

### Agent Composition: The Bridge Between Single and Multi-Agent

Before diving into formal orchestration patterns (Labs 06-10), agent composition provides a lightweight way to combine multiple agents. The key method is `.as_tool()` — it converts an agent into a function tool that another agent can call.

```
┌──────────────────────────────────────────────────────┐
│                 Agent Composition                     │
│                                                      │
│  ┌──────────────────┐                                │
│  │  Concierge Agent  │  "Plan my evening in Tokyo"   │
│  │  (main agent)     │                               │
│  └────┬─────────┬────┘                               │
│       │         │                                    │
│  .as_tool()  .as_tool()                              │
│       │         │                                    │
│  ┌────▼────┐ ┌──▼──────────┐                         │
│  │ Weather │ │ Restaurant  │                         │
│  │ Agent   │ │ Agent       │                         │
│  └─────────┘ └─────────────┘                         │
│                                                      │
│  Control ALWAYS returns to the Concierge Agent       │
└──────────────────────────────────────────────────────┘
```

### Agent-as-Tool vs Handoff

| Feature | Agent as Tool | Handoff (Lab 08) |
|---------|--------------|-----------------|
| **Control** | Returns to the primary agent | Transfers completely to the receiving agent |
| **Task ownership** | Primary agent retains responsibility | Receiving agent takes full ownership |
| **Context** | Primary agent manages overall context | Full context handed to next agent |
| **Best for** | Sub-task delegation | Domain routing |

---

## Setup

```bash
mkdir -p lab05 && cd lab05
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
Lab 05 — Agent as Tool
Microsoft Agent Framework Workshop

Demonstrates:
  - Converting an agent to a function tool with .as_tool()
  - Customizing tool name, description, and argument metadata
  - Building a hierarchical agent system (concierge pattern)
  - Combining agent-tools with regular function tools
"""

import asyncio
import os
from typing import Annotated

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pydantic import Field

from agent_framework import tool
from agent_framework.azure import AzureOpenAIResponsesClient

load_dotenv()


async def main():
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    # ── Sub-Agent 1: Weather Expert ──
    # This agent specializes in weather information.
    # It has its own tools for getting weather data.
    @tool(description="Get current weather for a city.")
    def get_weather(
        city: Annotated[str, Field(description="City name")],
    ) -> str:
        weather = {
            "tokyo": "22°C, sunny with clear skies",
            "paris": "18°C, partly cloudy with light breeze",
            "new york": "25°C, clear and humid",
            "london": "15°C, overcast with chance of rain",
        }
        return weather.get(city.lower(), f"{city}: 20°C, pleasant weather")

    weather_agent = client.as_agent(
        name="WeatherExpert",
        description="An expert agent that provides detailed weather reports.",
        instructions=(
            "You are a weather expert. When asked about weather, use your tools "
            "to get current conditions and provide a helpful, detailed report "
            "including what to wear and activity suggestions."
        ),
        tools=[get_weather],
    )

    # ── Sub-Agent 2: Restaurant Recommender ──
    # This agent specializes in restaurant recommendations.
    @tool(description="Search restaurants in a city by cuisine type.")
    def search_restaurants(
        city: Annotated[str, Field(description="City to search in")],
        cuisine: Annotated[str, Field(description="Cuisine type, e.g. 'japanese', 'french', 'italian'")] = "local",
    ) -> str:
        restaurants = {
            ("tokyo", "japanese"): (
                "1. Sukiyabashi Jiro - ★★★ Michelin, legendary sushi\n"
                "2. Ichiran Ramen - Famous tonkotsu ramen chain\n"
                "3. Gonpachi - Izakaya with stunning interior"
            ),
            ("tokyo", "local"): (
                "1. Tsukiji Outer Market - Fresh seafood stalls\n"
                "2. Afuri - Light yuzu shio ramen\n"
                "3. Yakitori Alley (Yurakucho) - Grilled skewers under the tracks"
            ),
            ("paris", "french"): (
                "1. Le Comptoir du Panthéon - Classic French bistro\n"
                "2. L'Ami Jean - Basque-influenced cuisine\n"
                "3. Bouillon Chartier - Historic budget-friendly French"
            ),
        }
        key = (city.lower(), cuisine.lower())
        result = restaurants.get(key, f"Top restaurants in {city}: Check local guides for {cuisine} options.")
        return f"Restaurants in {city} ({cuisine} cuisine):\n{result}"

    restaurant_agent = client.as_agent(
        name="RestaurantRecommender",
        description="An expert agent that recommends restaurants based on location and preferences.",
        instructions=(
            "You are a restaurant expert and food critic. When asked for "
            "restaurant recommendations, use your tools to find the best options "
            "and provide details about each restaurant including why you recommend it."
        ),
        tools=[search_restaurants],
    )

    # ── A regular function tool (not an agent) ──
    @tool(description="Get local events and activities in a city.")
    def get_local_events(
        city: Annotated[str, Field(description="City to search events in")],
    ) -> str:
        events = {
            "tokyo": (
                "Tonight in Tokyo:\n"
                "- Cherry Blossom Night Viewing at Ueno Park (free)\n"
                "- TeamLab Borderless Digital Art Exhibition\n"
                "- Live jazz at Blue Note Tokyo (8pm)"
            ),
            "paris": (
                "Tonight in Paris:\n"
                "- Seine River Dinner Cruise (7pm)\n"
                "- Late-night Louvre tour (Wednesdays & Fridays)\n"
                "- Jazz at Le Caveau de la Huchette (9pm)"
            ),
        }
        return events.get(city.lower(), f"Check local listings for events in {city}.")

    # ── Main Agent: Concierge ──
    # The concierge uses the sub-agents as tools.
    # .as_tool() converts each agent into a callable function tool.
    concierge = client.as_agent(
        name="Concierge",
        instructions=(
            "You are a luxury hotel concierge. Help guests plan their perfect "
            "evening by combining weather information, restaurant recommendations, "
            "and local events. Always create a cohesive itinerary that flows well. "
            "Use your specialist tools for each aspect of the planning."
        ),
        tools=[
            # Convert agents to tools with custom metadata
            weather_agent.as_tool(
                name="check_weather",
                description="Check weather conditions in a city to plan appropriately",
                arg_name="query",
                arg_description="The weather query, e.g. 'What's the weather in Tokyo tonight?'",
            ),
            restaurant_agent.as_tool(
                name="find_restaurants",
                description="Get restaurant recommendations for dining",
                arg_name="query",
                arg_description="Restaurant search query, e.g. 'Best Japanese restaurants in Tokyo'",
            ),
            # Mix agent-tools with regular function tools
            get_local_events,
        ],
    )

    # ── Demo 1: Simple delegation ──
    print("=" * 60)
    print("DEMO 1: Simple Delegation to Sub-Agent")
    print("=" * 60)
    result = await concierge.run("What's the weather like in Tokyo right now?")
    print(f"Agent: {result}\n")

    # ── Demo 2: Multi-agent coordination ──
    print("=" * 60)
    print("DEMO 2: Multi-Agent Coordination")
    print("=" * 60)
    result = await concierge.run(
        "Plan a perfect evening in Tokyo for me and my partner. "
        "We love Japanese food and want to experience local culture."
    )
    print(f"Agent: {result}\n")

    # ── Demo 3: Complex query requiring all tools ──
    print("=" * 60)
    print("DEMO 3: Complex Query (All Tools)")
    print("=" * 60)
    result = await concierge.run(
        "I'm visiting Paris tomorrow evening. Based on the weather, "
        "recommend whether we should dine outdoors or indoors, "
        "suggest a French restaurant, and find an evening activity."
    )
    print(f"Agent: {result}\n")


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
DEMO 1: Simple Delegation to Sub-Agent
============================================================
Agent: The weather in Tokyo right now is 22°C and sunny with clear skies.
It's a beautiful evening — perfect for outdoor dining or a stroll!

============================================================
DEMO 2: Multi-Agent Coordination
============================================================
Agent: Here's your perfect evening in Tokyo:

🌤️ **Weather**: 22°C, sunny and clear — a gorgeous evening!

🍣 **Dinner** (Japanese cuisine):
I recommend starting at Sukiyabashi Jiro for an unforgettable sushi experience,
or for a more casual vibe, try Gonpachi — a stunning izakaya...

🎭 **Evening Activities**:
- Cherry Blossom Night Viewing at Ueno Park (free and romantic!)
- TeamLab Borderless Digital Art Exhibition...

============================================================
DEMO 3: Complex Query (All Tools)
============================================================
Agent: Here's your Paris evening plan:

🌥️ **Weather**: 18°C, partly cloudy — I'd recommend indoor dining to be safe...
🍽️ **Restaurant**: Le Comptoir du Panthéon — a classic French bistro...
🎵 **Evening**: Jazz at Le Caveau de la Huchette at 9pm...
```

---

## Key Takeaways

1. **`agent.as_tool()`** converts any agent into a function tool that another agent can call.
2. **Customize tool metadata** with `name`, `description`, `arg_name`, and `arg_description`.
3. **Agent-tools and function tools mix freely** — combine them in a single agent's `tools` list.
4. **Control always returns** to the primary agent — unlike handoff, the sub-agent doesn't take over.
5. This pattern is ideal for **hierarchical delegation** — a concierge, dispatcher, or coordinator that routes sub-tasks.

---

## What's Next?

In **[Lab 06 — Sequential Orchestration](lab-06-sequential-orchestration.md)**, you'll learn the first formal multi-agent workflow pattern — agents executing in a defined pipeline order, each building on the previous agent's output.
