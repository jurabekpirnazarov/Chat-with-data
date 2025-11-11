import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from openai import OpenAI
from tools import query_database, create_support_ticket
import sqlite3
import os

# ✅ OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY") )

# 📊 Database path
DB_PATH = "data/orders.db"

# Streamlit page setup
st.set_page_config(page_title="🍕 Data Insights App", layout="wide")
st.title("🍕 Bellissimo Data Insights Agent")

st.sidebar.header("📂 Database Overview")

# 🔹 Database info
def get_db_info():
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql("SELECT * FROM orders LIMIT 5", conn)
        count = pd.read_sql("SELECT COUNT(*) as total FROM orders", conn)["total"][0]
        conn.close()
        return df, count
    except Exception as e:
        return None, str(e)

sample_df, total_rows = get_db_info()
st.sidebar.markdown(f"**Total Rows:** {total_rows}")
if isinstance(sample_df, pd.DataFrame):
    st.sidebar.dataframe(sample_df)
else:
    st.sidebar.error("Database not found or invalid.")

# 🔹 User input
user_query = st.text_input("💬 Ask your question about pizza sales:")

# 🔹 Action button
if st.button("Run Query"):
    if user_query.strip() == "":
        st.warning("Please enter a question first.")
    else:
        with st.spinner("🔍 Processing your request..."):
            try:
                # 🔹 LLM call
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": """You are a Data Insights Agent for Bellissimo Pizza.
You analyze a SQLite database with a single table: `orders`.

The table has these exact columns:
- id (INTEGER)
- customer_name (TEXT)
- item (TEXT)
- quantity (INTEGER)
- price (REAL)
- date (TEXT)

Rules:
1. Always use the correct column names.
2. To calculate total revenue, use (quantity * price).
3. Never use columns that don't exist.
4. Prefer aggregation queries like SUM, COUNT, AVG, GROUP BY, ORDER BY.
5. Return SQL that will work safely with SQLite.
"""
                        },
                        {"role": "user", "content": user_query}
                    ],
                    tools=[
                        {
                            "type": "function",
                            "function": {
                                "name": "query_database",
                                "description": "Safely query the database to retrieve data",
                                "parameters": {
                                    "type": "object",
                                    "properties": {"sql_query": {"type": "string"}},
                                    "required": ["sql_query"]
                                }
                            }
                        }
                    ]
                )

                # 🔹 Handle function call
                finish_reason = response.choices[0].finish_reason
                if finish_reason == "tool_calls":
                    tool_call = response.choices[0].message.tool_calls[0]
                    func_name = tool_call.function.name
                    func_args = eval(tool_call.function.arguments)

                    if func_name == "query_database":
                        result = query_database(**func_args)

                        if "error" in result:
                            st.error(f"❌ Error: {result['error']}")
                        else:
                            df = pd.DataFrame(result["rows"], columns=result["columns"])
                            st.success("✅ Query executed successfully!")
                            st.dataframe(df.head(20))

                            # 📊 Visualization
                            if "item" in df.columns and any(col in df.columns for col in ["quantity", "total_revenue"]):
                                st.subheader("📊 Top Ordered or Revenue-Generating Items")
                                fig, ax = plt.subplots()
                                if "total_revenue" in df.columns:
                                    df_sorted = df.sort_values("total_revenue", ascending=False).head(10)
                                    ax.bar(df_sorted["item"], df_sorted["total_revenue"])
                                    ax.set_ylabel("Total Revenue ($)")
                                else:
                                    grouped = df.groupby("item")["quantity"].sum().sort_values(ascending=False).head(10)
                                    grouped.plot(kind="bar", ax=ax)
                                    ax.set_ylabel("Total Quantity Sold")
                                plt.xticks(rotation=45)
                                st.pyplot(fig)
                    else:
                        st.warning("⚠️ Unknown tool requested by LLM.")

                else:
                    answer = response.choices[0].message.content
                    st.info(answer)

            except Exception as e:
                st.error(f"⚠️ Exception: {e}")
                # Offer support ticket creation
                if st.button("Create Support Ticket"):
                    ticket = create_support_ticket("Streamlit Agent Error", str(e))
                    if "url" in ticket:
                        st.success(f"Support ticket created: {ticket['url']}")
                    else:
                        st.error(ticket.get("error", "Unknown error"))

# Footer
st.markdown("---")
st.markdown("🧠 **Built by Jurabek Pirnazarov** — Bellissimo AI Team")
