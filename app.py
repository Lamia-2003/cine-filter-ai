import json
import os
import clickhouse_connect
from dotenv import load_dotenv
from google import genai
from google.genai import types
import pandas as pd
import streamlit as st

# تحميل المتغيرات الحساسة من ملف .env
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

st.set_page_config(
    page_title="CineFilter AI", page_icon="🎬", layout="wide"
)

st.title("🎬 CineFilter AI - Scene Analysis & Safety Agent")
st.write("مستشار أمان المحتوى السينمائي المدعوم بـ Gemini 3.6 & ClickHouse Cloud")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 إدخال تفاصيل المشهد")
    movie_title = st.text_input("اسم الفيلم / العمل", "The Blockbuster Movie")
    c1, c2 = st.columns(2)
    start_time = c1.text_input("بداية المشهد", "00:14:20")
    end_time = c2.text_input("نهاية المشهد", "00:15:05")

    scene_desc = st.text_area(
        "وصف المشهد أو النص (Script / Subtitle)",
        "Character A loses their temper, screams offensive profanity at B, and"
        " throws a wooden chair across the dining room.",
        height=150,
    )

    if st.button("🚀 تحليل المشهد وحفظه"):
        with st.spinner("جاري التحليل بواسطة Gemini..."):
            prompt = f"""
            You are an AI safety agent for media filtering.
            Analyze the following scene script/description:
            "{scene_desc}"

            Respond strictly with a VALID JSON object containing:
            - contains_inappropriate: boolean
            - category: string
            - recommendation: string
            """
            config = types.GenerateContentConfig(
                response_mime_type="application/json"
            )
            response = gemini_client.models.generate_content(
                model="gemini-3.6-flash", contents=prompt, config=config
            )

            analysis = json.loads(response.text)

            is_flagged = (
                1 if analysis.get("contains_inappropriate", False) else 0
            )
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
            st.success("تم التحليل والحفظ بنجاح في ClickHouse!")
            st.json(analysis)

with col2:
    st.subheader("📊 المشاهد المحللة مؤخراً (من ClickHouse)")
    if st.button("🔄 تحديث الجدول"):
        st.rerun()

    query_res = ch_client.query(
        "SELECT movie_title, timestamp_start, timestamp_end,"
        " contains_inappropriate, category, recommendation, created_at FROM"
        " scene_analyses ORDER BY created_at DESC LIMIT 10"
    )

    df = pd.DataFrame(
        query_res.result_set,
        columns=[
            "Movie",
            "Start",
            "End",
            "Inappropriate",
            "Category",
            "Recommendation",
            "Created At",
        ],
    )
    st.dataframe(df, use_container_width=True)