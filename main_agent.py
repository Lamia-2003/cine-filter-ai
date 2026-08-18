import json
import clickhouse_connect
from google import genai

# 1. إعداد مفاتيح الاتصال
GEMINI_API_KEY = "AQ.Ab8RN6LU2HII3RRaLrWuaQWpqI83krjjfgNziokzFh1p8ZTP4A"

CLICKHOUSE_HOST = "euc1c1p1aw.europe-west2.gcp.clickhouse.cloud"
CLICKHOUSE_USER = "default"
CLICKHOUSE_PASS = "JjRypBwYE.Kc4"


# 2. تهيئة العملاء (Clients)
def init_clients():
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    ch_client = clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=8443,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASS,
        secure=True,
    )
    return gemini_client, ch_client


# 3. إنشاء جدول البيانات في ClickHouse إذا لم يكن موجوداً
def setup_database(ch_client):
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
    print("[DB] الجدول في ClickHouse جاهز لاستقبال البيانات.")


# 4. تحليل المشهد باستخدام Gemini
def analyze_scene_with_gemini(gemini_client, scene_text):
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

    # تنظيف وتنسيق نص الـ JSON
    clean_json_text = (
        response.text.replace("```json", "").replace("```", "").strip()
    )
    return json.loads(clean_json_text)


# 5. حفظ النتيجة في ClickHouse
def save_to_clickhouse(
    ch_client, movie_title, start_time, end_time, analysis
):
    is_flagged = 1 if analysis.get("contains_inappropriate", False) else 0

    insert_query = """
    INSERT INTO scene_analyses 
    (movie_title, timestamp_start, timestamp_end, contains_inappropriate, category, recommendation) 
    VALUES
    """
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
    print(f"[DB] تم حفظ تحليل المشهد ({start_time} - {end_time}) بنجاح!")


# --- تشغيل التجربة ---
if __name__ == "__main__":
    gemini_client, ch_client = init_clients()
    setup_database(ch_client)

    # مشهد تجريبي
    sample_movie = "The Blockbuster Movie"
    sample_start = "00:14:20"
    sample_end = "00:15:05"
    sample_scene_description = (
        "Character A loses their temper, screams offensive profanity at B, and"
        " throws a wooden chair across the dining room."
    )

    print("\n--- جاري تحليل المشهد بواسطة Gemini ---")
    analysis = analyze_scene_with_gemini(
        gemini_client, sample_scene_description
    )
    print("نتيجة التحليل:", analysis)

    print("\n--- جاري إرسال النتيجة إلى ClickHouse ---")
    save_to_clickhouse(
        ch_client, sample_movie, sample_start, sample_end, analysis
    )

    # عرض البيانات المخزنة للتأكد
    result = ch_client.query("SELECT * FROM scene_analyses LIMIT 5")
    print("\n--- البيانات المخزنة حالياً في ClickHouse ---")
    print(result.result_set)