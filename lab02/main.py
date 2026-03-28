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


def get_weather(
    location: Annotated[str, Field(description="City name, e.g. 'Tokyo' or 'Paris'")],
    unit: Annotated[str, Field(description="Temperature unit: 'celsius' or 'fahrenheit'")] = "celsius",
) -> str:
    """Get the current weather for a given location."""
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


@tool(name="search_flights", description="Search for available flights between two cities on a given date.")
def search_flights(
    origin: Annotated[str, Field(description="Departure city")],
    destination: Annotated[str, Field(description="Arrival city")],
    date: Annotated[str, Field(description="Travel date in YYYY-MM-DD format")],
) -> str:
    """Search for flights."""
    flights = [
        {"airline": "AirGlobal", "departure": "08:30", "arrival": "14:45", "price": 450},
        {"airline": "SkyWings", "departure": "12:00", "arrival": "18:15", "price": 380},
        {"airline": "OceanAir", "departure": "16:30", "arrival": "22:45", "price": 520},
    ]
    result = f"Flights from {origin} to {destination} on {date}:\n"
    for f in flights:
        result += f"  - {f['airline']}: {f['departure']}-{f['arrival']}, ${f['price']}\n"
    return result


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


@tool(description="Get personalized travel recommendations based on user preferences.")
def get_recommendations(
    destination: Annotated[str, Field(description="City to get recommendations for")],
    ctx: FunctionInvocationContext,
) -> str:
    """Get travel recommendations with user context."""
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
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    hotel_service = HotelService(currency="USD")

    agent = client.as_agent(
        name="TravelAssistant",
        instructions=(
            "You are a helpful travel assistant. You can check weather, "
            "search flights and hotels, book hotels, and give travel recommendations. "
            "Always be helpful and provide specific details from the tools."
        ),
        tools=[
            get_weather,
            search_flights,
            hotel_service.search_hotels,
            hotel_service.book_hotel,
            get_recommendations,
        ],
    )

    # Demo 1: Weather check
    print("=" * 60)
    print("DEMO 1: Weather Check (Plain Function Tool)")
    print("=" * 60)
    result = await agent.run("What's the weather like in Tokyo and Paris?")
    print(f"Agent: {result}\n")

    # Demo 2: Flight search
    print("=" * 60)
    print("DEMO 2: Flight Search (@tool Decorated)")
    print("=" * 60)
    result = await agent.run("Find me flights from New York to Tokyo on 2026-05-15")
    print(f"Agent: {result}\n")

    # Demo 3: Hotel search + booking
    print("=" * 60)
    print("DEMO 3: Hotel Search & Booking (Class-Based Tools)")
    print("=" * 60)
    result = await agent.run(
        "Search for hotels in Tokyo from 2026-05-15 to 2026-05-20, "
        "then book the Grand Plaza for John Smith"
    )
    print(f"Agent: {result}")
    print(f"\nBookings in system: {hotel_service.bookings}\n")

    # Demo 4: Recommendations with runtime context
    print("=" * 60)
    print("DEMO 4: Recommendations (FunctionInvocationContext)")
    print("=" * 60)
    result = await agent.run(
        "Give me recommendations for Tokyo",
        function_invocation_kwargs={"user_id": "user_42", "preference": "food"},
    )
    print(f"Agent: {result}\n")

    # Demo 5: Complex multi-tool query
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
