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

    # Sub-Agent 1: Weather Expert
    @tool(description="Get current weather for a city.")
    def get_weather(city: Annotated[str, Field(description="City name")]) -> str:
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

    # Sub-Agent 2: Restaurant Recommender
    @tool(description="Search restaurants in a city by cuisine type.")
    def search_restaurants(
        city: Annotated[str, Field(description="City to search in")],
        cuisine: Annotated[str, Field(description="Cuisine type")] = "local",
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
        description="An expert agent that recommends restaurants.",
        instructions=(
            "You are a restaurant expert and food critic. Use your tools to find "
            "the best options and provide details about each restaurant."
        ),
        tools=[search_restaurants],
    )

    # Regular function tool
    @tool(description="Get local events and activities in a city.")
    def get_local_events(city: Annotated[str, Field(description="City name")]) -> str:
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

    # Main Agent: Concierge
    concierge = client.as_agent(
        name="Concierge",
        instructions=(
            "You are a luxury hotel concierge. Help guests plan their perfect "
            "evening by combining weather information, restaurant recommendations, "
            "and local events. Always create a cohesive itinerary."
        ),
        tools=[
            weather_agent.as_tool(
                name="check_weather",
                description="Check weather conditions in a city",
                arg_name="query",
                arg_description="The weather query",
            ),
            restaurant_agent.as_tool(
                name="find_restaurants",
                description="Get restaurant recommendations for dining",
                arg_name="query",
                arg_description="Restaurant search query",
            ),
            get_local_events,
        ],
    )

    # Demo 1: Simple delegation
    print("=" * 60)
    print("DEMO 1: Simple Delegation to Sub-Agent")
    print("=" * 60)
    result = await concierge.run("What's the weather like in Tokyo right now?")
    print(f"Agent: {result}\n")

    # Demo 2: Multi-agent coordination
    print("=" * 60)
    print("DEMO 2: Multi-Agent Coordination")
    print("=" * 60)
    result = await concierge.run(
        "Plan a perfect evening in Tokyo for me and my partner. "
        "We love Japanese food and want to experience local culture."
    )
    print(f"Agent: {result}\n")

    # Demo 3: Complex query requiring all tools
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
