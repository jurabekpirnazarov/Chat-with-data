import sqlite3
import logging
import requests
import os

# Loglarni sozlash
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DB_PATH = "data/orders.db"


# 1️⃣ Ma’lumotlar bazasidan so‘rovni o‘qish (safety check bilan)
def query_database(sql_query: str):
    sql_query_lower = sql_query.lower()
    dangerous_words = ["delete", "drop", "update", "insert", "alter"]

    if any(word in sql_query_lower for word in dangerous_words):
        logging.warning("❌ Xavfli so‘rov aniqlangan! Operatsiya bekor qilindi.")
        return {"error": "Dangerous SQL operation blocked."}

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        logging.info(f"🔍 Query bajarilmoqda: {sql_query}")
        cursor.execute(sql_query)
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()
        conn.close()
        logging.info(f"✅ {len(results)} ta natija topildi.")
        return {"columns": columns, "rows": results}
    except Exception as e:
        logging.error(f"❌ Xato: {e}")
        return {"error": str(e)}


# 2️⃣ Support ticket yaratish (GitHub Issues misolida)
def create_support_ticket(title: str, body: str):
    try:
        token = os.getenv("GITHUB_TOKEN")
        repo = os.getenv("GITHUB_REPO", "jurabek-pirnazarov/data-insights-support")
        url = f"https://api.github.com/repos/{repo}/issues"
        headers = {"Authorization": f"token {token}"}
        data = {"title": title, "body": body}

        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 201:
            issue_url = response.json().get("html_url")
            logging.info(f"✅ Support ticket yaratildi: {issue_url}")
            return {"message": "Support ticket created successfully", "url": issue_url}
        else:
            logging.error(f"❌ Ticket yaratishda xato: {response.text}")
            return {"error": response.text}
    except Exception as e:
        logging.error(f"❌ Exception: {e}")
        return {"error": str(e)}
