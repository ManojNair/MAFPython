# Lab 02 — Function Tools

## Objective

Extend your agent with **custom Python functions** (tools) that the LLM can call during a conversation. You'll build a travel assistant that can check weather, search flights, and look up hotel availability — all through tools the model intelligently invokes when needed.

---

## Concepts

### What Are Function Tools?

Function tools let you give your agent **real-world capabilities**. Instead of the model guessing or hallucinating answers about live data, it can call your Python functions to fetch actual information.

```
┌──────────────────────────────────────────────────────────────┐
│                     Agent with Tools                         │
│                                                              │
│  User: "What's the weather in Tokyo?"                        │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐     ┌──────────────────────┐            │
│  │   LLM Reasoning │────►│  Tool: get_weather() │            │
│  │   "I should     │     │  location="Tokyo"    │            │
│  │    check the    │     └──────────┬───────────┘            │
│  │    weather"     │                │                        │
│  │                 │◄───────────────┘                        │
│  │  "It's 22°C    │     Returns: "22°C, sunny"              │
│  │   and sunny"   │                                          │
│  └─────────────────┘                                         │
└──────────────────────────────────────────────────────────────┘
```

The flow is:
1. User sends a message
2. LLM decides it needs information from a tool
3. Framework automatically calls your Python function
4. Result is fed back to the LLM
5. LLM generates a natural language response incorporating the tool result

### Ways to Define Tools

| Method | When to Use |
|--------|-------------|
| **Plain function** | Simplest — just pass a Python function |
| **`@tool` decorator** | When you need custom name, description, or approval mode |
| **Pydantic schema** | When you need full control over the input schema |
| **Class methods** | When tools share state (e.g., database connection, API client) |

---

## Setup

```bash
mkdir -p lab02 && cd lab02
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
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
Lab 02 — Function Tools
Microsoft Agent Framework Workshop

Demonstrates:
  - Simple function tools (plain functions)
  - @tool decorator with name and description
  - Annotated types with Pydantic Field for parameter descriptions
  - Class-based tools with shared state
  - FunctionInvocationContext for runtime-only values
"""

import asyncio
import os
from typing import Annotated

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pydantic import Field

from agent_framework import tool, FunctionInvocationContext
from agent_framework.azure import AzureOpenAIResponsesClient

load_dotenv()


# ──────────────────────────────────────────────
# Tool Definitions
# ──────────────────────────────────────────────


# APPROACH 1: Plain function with Annotated type hints
# The function name becomes the tool name, the docstring becomes the description.
# Annotated[type, Field(description=...)] tells the LLM what each parameter means.
def get_weather(
    location: Annotated[str, Field(description="City name, e.g. 'Tokyo' or 'Paris'")],
    unit: Annotated[str, Field(description="Temperature unit: 'celsius' or 'fahrenheit'")] = "celsius",
) -> str:
    """Get the current weather for a given location."""
    # In production, this would call a real weather API
    weather_data = {
        "tokyo": {"temp": 22, "condition": "sunny", "humidity": 45},
        "paris": {"temp": 18, "condition": "partly cloudy", "humidity": 60},
        "new york": {"temp": 25, "condition": "clear", "humidity": 55},
        "london": {"temp": 15, "condition": "rainy", "humidity": 80},
    }

    data = weather_data.get(location.lower(), {"temp": 20, "condition": "unknown", "humidity": 50})
    temp = data["temp"] if unit == "celsius" else int(data["temp"] * 9 / 5 + 32)
    symbol = "°C" if unit == "celsius" else "°F"

    return f"Weather in {location}: {data['condition']}, {temp}{symbol}, humidity {data['humidity']}%"


# APPROACH 2: @tool decorator for explicit name and description
# Use this when you want the tool name to differ from the function name,
# or when you want a more detailed description than the docstring.
@tool(
    name="search_flights",
    description="Search for available flights between two cities on a given date.",
)
def search_flights(
    origin: Annotated[str, Field(description="Departure city")],
    destination: Annotated[str, Field(description="Arrival city")],
    date: Annotated[str, Field(description="Travel date in YYYY-MM-DD format")],
) -> str:
    """Search for flights."""
    # Simulated flight data
    flights = [
        {"airline": "AirGlobal", "departure": "08:30", "arrival": "14:45", "price": 450},
        {"airline": "SkyWings", "departure": "12:00", "arrival": "18:15", "price": 380},
        {"airline": "OceanAir", "departure": "16:30", "arrival": "22:45", "price": 520},
    ]

    result = f"Flights from {origin} to {destination} on {date}:\n"
    for f in flights:
        result += f"  - {f['airline']}: {f['departure']}-{f['arrival']}, ${f['price']}\n"
    return result


# APPROACH 3: Class-based tools with shared state
# When tools share a database connection, API client, or configuration,
# wrap them in a class. Class attributes are hidden from the LLM.
class HotelService:
    """Hotel booking service with shared state."""

    def __init__(self, currency: str = "USD"):
        self.currency = currency
        self.bookings: list[dict] = []

    @tool(description="Search for available hotels in a city for given dates.")
    def search_hotels(
        self,
        city: Annotated[str, Field(description="City to search hotels in")],
        check_in: Annotated[str, Field(description="Check-in date (YYYY-MM-DD)")],
        check_out: Annotated[str, Field(description="Check-out date (YYYY-MM-DD)")],
    ) -> str:
        """Search hotels."""
        hotels = [
            {"name": "Grand Plaza", "rating": 4.5, "price": 180},
            {"name": "City Center Inn", "rating": 4.0, "price": 120},
            {"name": "Budget Stay", "rating": 3.5, "price": 75},
        ]

        result = f"Hotels in {city} ({check_in} to {check_out}):\n"
        for h in hotels:
            result += f"  - {h['name']}: ★{h['rating']}, {self.currency} {h['price']}/night\n"
        return result

    @tool(description="Book a hotel room. Returns a confirmation number.")
    def book_hotel(
        self,
        hotel_name: Annotated[str, Field(description="Name of the hotel to book")],
        guest_name: Annotated[str, Field(description="Name of the guest")],
    ) -> str:
        """Book a hotel."""
        confirmation = f"CONF-{len(self.bookings) + 1001}"
        self.bookings.append({
            "hotel": hotel_name,
            "guest": guest_name,
            "confirmation": confirmation,
        })
        return f"Booking confirmed! Hotel: {hotel_name}, Guest: {guest_name}, Confirmation: {confirmation}"


# APPROACH 4: Tool with FunctionInvocationContext for runtime injection
# Use this when the tool needs values that change per invocation (e.g., user ID)
# but shouldn't be exposed to the LLM.
@tool(description="Get personalized travel recommendations based on user preferences.")
def get_recommendations(
    destination: Annotated[str, Field(description="City to get recommendations for")],
    ctx: FunctionInvocationContext,
) -> str:
    """Get travel recommendations with user context."""
    # ctx.kwargs contains runtime-only values passed via function_invocation_kwargs
    user_id = ctx.kwargs.get("user_id", "anonymous")
    preference = ctx.kwargs.get("preference", "general")

    recommendations = {
        "tokyo": {
            "culture": "Visit Senso-ji Temple, explore Akihabara, attend a tea ceremony",
            "food": "Try ramen at Ichiran, visit Tsukiji Market, experience an izakaya",
            "general": "See the Shibuya Crossing, visit Meiji Shrine, explore Shinjuku",
        },
        "paris": {
            "culture": "Visit the Louvre, explore Montmartre, see Notre-Dame",
            "food": "Try croissants at Du Pain et des Idées, dine in Le Marais",
            "general": "See the Eiffel Tower, cruise the Seine, visit Versailles",
        },
    }

    city_recs = recommendations.get(destination.lower(), {})
    rec = city_recs.get(preference, f"Explore the local culture and cuisine of {destination}!")

    return f"Recommendations for {destination} (user: {user_id}, style: {preference}): {rec}"


async def main():
    # Create the client
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    # Initialize the hotel service (class-based tools with shared state)
    hotel_service = HotelService(currency="USD")

    # Create the travel assistant agent with ALL tools
    agent = client.as_agent(
        name="TravelAssistant",
        instructions=(
            "You are a helpful travel assistant. You can check weather, "
            "search flights and hotels, book hotels, and give travel recommendations. "
            "Always be helpful and provide specific details from the tools."
        ),
        tools=[
            get_weather,                        # Plain function
            search_flights,                     # @tool decorated
            hotel_service.search_hotels,        # Class method
            hotel_service.book_hotel,           # Class method
            get_recommendations,                # With context injection
        ],
    )

    # ── Demo 1: Weather check (plain function tool) ──
    print("=" * 60)
    print("DEMO 1: Weather Check (Plain Function Tool)")
    print("=" * 60)
    result = await agent.run("What's the weather like in Tokyo and Paris?")
    print(f"Agent: {result}\n")

    # ── Demo 2: Flight search (@tool decorated) ──
    print("=" * 60)
    print("DEMO 2: Flight Search (@tool Decorated)")
    print("=" * 60)
    result = await agent.run("Find me flights from New York to Tokyo on 2026-05-15")
    print(f"Agent: {result}\n")

    # ── Demo 3: Hotel search + booking (class-based tools) ──
    print("=" * 60)
    print("DEMO 3: Hotel Search & Booking (Class-Based Tools)")
    print("=" * 60)
    result = await agent.run(
        "Search for hotels in Tokyo from 2026-05-15 to 2026-05-20, "
        "then book the Grand Plaza for John Smith"
    )
    print(f"Agent: {result}")
    print(f"\nBookings in system: {hotel_service.bookings}\n")

    # ── Demo 4: Recommendations with runtime context ──
    print("=" * 60)
    print("DEMO 4: Recommendations (FunctionInvocationContext)")
    print("=" * 60)
    result = await agent.run(
        "Give me recommendations for Tokyo",
        function_invocation_kwargs={"user_id": "user_42", "preference": "food"},
    )
    print(f"Agent: {result}\n")

    # ── Demo 5: Complex multi-tool query ──
    print("=" * 60)
    print("DEMO 5: Complex Multi-Tool Query")
    print("=" * 60)
    result = await agent.run(
        "I'm planning a trip to Paris next month. Can you check the weather, "
        "find flights from London to Paris on 2026-04-20, and search for "
        "hotels from April 20-25?"
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
DEMO 1: Weather Check (Plain Function Tool)
============================================================
Agent: Here's the current weather:
- Tokyo: sunny, 22°C, humidity 45%
- Paris: partly cloudy, 18°C, humidity 60%

============================================================
DEMO 2: Flight Search (@tool Decorated)
============================================================
Agent: Here are the available flights from New York to Tokyo on 2026-05-15:
- AirGlobal: 08:30-14:45, $450
- SkyWings: 12:00-18:15, $380
- OceanAir: 16:30-22:45, $520
The most affordable option is SkyWings at $380.

============================================================
DEMO 3: Hotel Search & Booking (Class-Based Tools)
============================================================
Agent: I found these hotels in Tokyo (May 15-20):
- Grand Plaza: ★4.5, $180/night
- City Center Inn: ★4.0, $120/night
- Budget Stay: ★3.5, $75/night

I've booked the Grand Plaza for John Smith. Confirmation: CONF-1001

Bookings in system: [{'hotel': 'Grand Plaza', 'guest': 'John Smith', 'confirmation': 'CONF-1001'}]

============================================================
DEMO 4: Recommendations (FunctionInvocationContext)
============================================================
Agent: Here are food recommendations for Tokyo:
Try ramen at Ichiran, visit Tsukiji Market, experience an izakaya...

============================================================
DEMO 5: Complex Multi-Tool Query
============================================================
Agent: Here's your Paris trip planning summary:
**Weather:** Partly cloudy, 18°C...
**Flights from London (Apr 20):** ...
**Hotels (Apr 20-25):** ...
```

---

## Deep Dive: How Tool Calling Works

### The Tool Call Loop

When the LLM encounters a question it can't answer from its training data, it enters a **tool call loop**:

```
User message ──► LLM reasons ──► Tool call decision
                                       │
                    ┌──────────────────┘
                    ▼
              Execute function ──► Result back to LLM
                                       │
                    ┌──────────────────┘
                    ▼
              LLM generates final response
              (may call more tools if needed)
```

### Tool Schema Generation

When you pass a function to the agent, the framework automatically generates a JSON schema from:
- **Function name** → tool name
- **Docstring** → tool description
- **`Annotated[type, Field(description=...)]`** → parameter descriptions
- **Default values** → optional parameters
- **Return type** → expected output type

This schema is sent to the LLM so it knows what tools are available and how to call them.

---

## Key Takeaways

1. **Plain functions** are the simplest way to create tools — just pass them to `tools=[...]`.
2. **`@tool` decorator** gives you explicit control over name, description, and approval mode.
3. **`Annotated[type, Field(description=...)]`** provides rich parameter descriptions to the LLM.
4. **Class-based tools** share state (connections, caches) between multiple tool functions.
5. **`FunctionInvocationContext`** injects runtime-only values hidden from the LLM.
6. The agent automatically decides which tools to call based on the user's message — you don't need to route manually.

---

## What's Next?

In **[Lab 03 — MCP Tools Integration](lab-03-mcp-tools.md)**, you'll connect your agent to external tool servers using the **Model Context Protocol (MCP)**, including the **Microsoft Learn MCP server** for real documentation search.
