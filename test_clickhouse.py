import os
import clickhouse_connect
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASS = os.getenv("CLICKHOUSE_PASS")

# Establish connection to ClickHouse Cloud
client = clickhouse_connect.get_client(
    host=CLICKHOUSE_HOST,
    port=8443,
    user=CLICKHOUSE_USER,
    password=CLICKHOUSE_PASS,
    secure=True,
)

# Test connection query
result = client.query("SELECT 'ClickHouse Connected Successfully!' AS message")

print("--- ClickHouse Response ---")
print(result.result_set[0][0])