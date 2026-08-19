import json
import os
import clickhouse_connect
from dotenv import load_dotenv
from google import genai

# 1. Load Environment Variables
load_dotenv()

# We pass the Variable NAMES into getenv(), not the actual key values
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASS = os.getenv("CLICKHOUSE_PASS")

# 2. Initialize Clients
def init_clients():
    """Initializes and returns Gemini and ClickHouse client instances."""
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    ch_client = clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=8443,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASS,
        secure=True,
    )
    return gemini_client, ch_client


# 3. Setup ClickHouse Database Table
def setup_database(ch_client):
    """Creates the scene_analyses table in ClickHouse if it doesn't already exist."""
    create_table_query = """
    CREATE TABLE IF NOT EXISTS scene_analyses (
        movie_title String,
        timestamp_start String,
        timestamp_end String,
        contains_inappropriate UInt8,
        category String,
        recommendation String,
        created_at DateTime DEFAULT now()
    ) ENGINE = MergeTree()
    ORDER BY (movie_title, created_at);
    """
    ch_client.command(create_table_query)
    print("[DB] ClickHouse table is ready for data ingestion.")


# 4. Analyze Scene Content with Gemini
def analyze_scene_with_gemini(gemini_client, scene_text):
    """Sends the scene script or description to Gemini for safety analysis."""
    prompt = f"""
    You are an AI safety agent for media filtering.
    Analyze the following scene script/description:
    "{scene_text}"

    Respond strictly with a VALID JSON object (no markdown, no extra code blocks) containing:
    - contains_inappropriate: boolean
    - category: string (e.g. "violence", "profanity", "none")
    - recommendation: string
    """

    response = gemini_client.models.generate_content(
        model="gemini-3.6-flash", contents=prompt
    )

    # Clean and parse the raw JSON string
    clean_json_text = (
        response.text.replace("```json", "").replace("```", "").strip()
    )
    return json.loads(clean_json_text)


# 5. Save Analysis Result to ClickHouse
def save_to_clickhouse(
    ch_client, movie_title, start_time, end_time, analysis
):
    """Inserts the parsed safety analysis into the ClickHouse database."""
    is_flagged = 1 if analysis.get("contains_inappropriate", False) else 0

    data = [(
        movie_title,
        start_time,
        end_time,
        is_flagged,
        analysis.get("category", "none"),
        analysis.get("recommendation", ""),
    )]

    ch_client.insert(
        "scene_analyses",
        data,
        column_names=[
            "movie_title",
            "timestamp_start",
            "timestamp_end",
            "contains_inappropriate",
            "category",
            "recommendation",
        ],
    )
    print(
        f"[DB] Scene analysis ({start_time} - {end_time}) saved successfully!"
    )


# --- Main Execution Pipeline ---
if __name__ == "__main__":
    gemini_client, ch_client = init_clients()
    setup_database(ch_client)

    # Sample test data
    sample_movie = "The Blockbuster Movie"
    sample_start = "00:14:20"
    sample_end = "00:15:05"
    sample_scene_description = (
        "Character A loses their temper, screams offensive profanity at B, and"
        " throws a wooden chair across the dining room."
    )

    print("\n--- Analyzing scene using Gemini 3.6 ---")
    analysis = analyze_scene_with_gemini(
        gemini_client, sample_scene_description
    )
    print("Analysis Result:", analysis)

    print("\n--- Saving result to ClickHouse Cloud ---")
    save_to_clickhouse(
        ch_client, sample_movie, sample_start, sample_end, analysis
    )

    # Fetch stored records to verify
    result = ch_client.query("SELECT * FROM scene_analyses LIMIT 5")
    print("\n--- Current Records in ClickHouse DB ---")
    print(result.result_set)