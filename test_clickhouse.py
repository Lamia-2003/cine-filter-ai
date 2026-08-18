import clickhouse_connect

# الاتصال بقاعدة البيانات
client = clickhouse_connect.get_client(
    host='euc1c1p1aw.europe-west2.gcp.clickhouse.cloud',
    port=8443,
    user='default',
    password='JjRypBwYE.Kc4',
    secure=True
)

# اختبار الاستعلام
result = client.query("SELECT 'ClickHouse Connected Successfully!' AS message")
print("--- استجابة ClickHouse ---")
print(result.result_set[0][0])