import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables from .env file
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

# Define prompt and scene content
scene_description = (
    "Two actors are arguing, one uses vulgar language and throws a glass."
)

prompt = f"""
You are an AI safety agent for movies. Analyze this scene:
"{scene_description}"

Return a valid JSON object containing:
1. contains_inappropriate_content (boolean)
2. category (string: profanity/violence/none/etc)
3. recommendation (string)
"""

# Force valid JSON response format
config = types.GenerateContentConfig(
    response_mime_type="application/json"
)

# Call Gemini API
response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=prompt,
    config=config
)

print("--- Gemini Response ---")
print(response.text)