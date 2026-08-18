import os
from google import genai

API_KEY = "AQ.Ab8RN6LU2HII3RRaLrWuaQWpqI83krjjfgNziokzFh1p8ZTP4A"

client = genai.Client(api_key=API_KEY)

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=(
        "You are an AI safety agent for movies. Analyze this short scene:"
        " 'Two actors are arguing, one uses vulgar language and throws a glass.'"
        " Return a JSON with: 1. contains_inappropriate_content (true/false),"
        " 2. category (profanity/violence/etc), 3. recommendation."
    ),
)

print("--- استجابة Gemini ---")
print(response.text)