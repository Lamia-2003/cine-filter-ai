import json
import os
import re
import clickhouse_connect
from dotenv import load_dotenv
from google import genai
from google.genai import types
import pandas as pd
import streamlit as st

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASS = os.getenv("CLICKHOUSE_PASS")


@st.cache_resource
def get_clients():
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    ch_client = clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=8443,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASS,
        secure=True,
    )
    return gemini_client, ch_client


gemini_client, ch_client = get_clients()


def parse_srt_into_chunks(file_content: str, max_lines_per_chunk=40):
    """Parses SRT into smaller timestamped scene chunks for granular analysis."""
    blocks = file_content.strip().split("\n\n")
    chunks = []
    current_lines = []
    start_time = None
    end_time = None

    for block in blocks:
        lines = block.splitlines()
        if len(lines) >= 3 and "-->" in lines[1]:
            timestamps = lines[1].split("-->")
            curr_start = timestamps[0].strip().split(",")[0]
            curr_end = timestamps[1].strip().split(",")[0]

            if not start_time:
                start_time = curr_start
            end_time = curr_end

            # Join subtitle text
            text = " ".join(lines[2:])
            current_lines.append(text)

            if len(current_lines) >= max_lines_per_chunk:
                chunks.append({
                    "start": start_time,
                    "end": end_time,
                    "text": " ".join(current_lines),
                })
                current_lines = []
                start_time = None

    if current_lines:
        chunks.append({
            "start": start_time or "00:00:00",
            "end": end_time or "00:00:00",
            "text": " ".join(current_lines),
        })

    return chunks


st.set_page_config(
    page_title="CineFilter AI | Cinema Safety Agent",
    page_icon="🎬",
    layout="wide",
)

st.markdown(
    '<h1 style="color: #E50914;">🎬 CineFilter AI - Automated Content'
    " Moderation</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<b>Granular Subtitle & Script Safety Parser powered by Gemini 3.6 &"
    " ClickHouse Cloud</b>",
    unsafe_allow_html=True,
)
st.divider()

col_input, col_table = st.columns([1, 1.2], gap="large")

with col_input:
    st.subheader("📝 Scene Analysis & File Upload")
    movie_title = st.text_input(
        "Movie / Media Title", "Spider-Man: Far From Home"
    )

    uploaded_file = st.file_uploader(
        "Upload Subtitle File (.srt)", type=["srt"]
    )

    if uploaded_file is not None:
        raw_content = uploaded_file.read().decode("utf-8", errors="ignore")
        chunks = parse_srt_into_chunks(raw_content, max_lines_per_chunk=35)

        st.success(f"Parsed {len(chunks)} distinct scenes/chunks from file!")

        selected_chunk_idx = st.selectbox(
            "Select Scene Chunk to Preview / Analyze:",
            options=range(len(chunks)),
            format_func=lambda i: (
                f"Scene {i+1}: ({chunks[i]['start']} - {chunks[i]['end']})"
            ),
        )

        active_chunk = chunks[selected_chunk_idx]

        scene_desc = st.text_area(
            "Extracted Subtitle Text", active_chunk["text"], height=160
        )
        start_time = st.text_input("Start Time", active_chunk["start"])
        end_time = st.text_input("End Time", active_chunk["end"])

        if st.button("🚀 Analyze & Log Selected Scene", use_container_width=True):
            with st.spinner("Analyzing scene chunk with Gemini 3.6..."):
                try:
                    prompt = f"""
                    You are an expert media moderation AI agent.
                    Analyze this specific movie scene subtitle chunk:
                    "{scene_desc}"

                    Respond strictly with a VALID JSON object containing:
                    - contains_inappropriate: boolean
                    - category: string (e.g. 'Violence', 'Profanity', 'Sexual Content', 'None')
                    - recommendation: string (actionable advice, e.g. 'Mute Audio', 'Skip Scene', 'Approved for All')
                    """

                    config = types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                    response = gemini_client.models.generate_content(
                        model="gemini-3.6-flash", contents=prompt, config=config
                    )

                    analysis = json.loads(response.text)
                    is_flagged = (
                        1
                        if analysis.get("contains_inappropriate", False)
                        else 0
                    )

                    data = [(
                        movie_title,
                        start_time,
                        end_time,
                        is_flagged,
                        analysis.get("category", "None"),
                        analysis.get("recommendation", "N/A"),
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

                    st.success("Analysis logged successfully!")
                    st.json(analysis)

                except Exception as e:
                    st.error(f"Error analyzing scene: {e}")

with col_table:
    st.subheader("📊 Recent Moderation Logs")
    if st.button("🔄 Refresh Data"):
        st.rerun()

    try:
        query_res = ch_client.query(
            "SELECT movie_title, timestamp_start, timestamp_end,"
            " contains_inappropriate, category, recommendation, created_at FROM"
            " scene_analyses ORDER BY created_at DESC LIMIT 15"
        )
        df = pd.DataFrame(
            query_res.result_set,
            columns=[
                "Movie Title",
                "Start",
                "End",
                "Inappropriate",
                "Category",
                "Recommendation",
                "Created At",
            ],
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Failed to fetch records: {e}")