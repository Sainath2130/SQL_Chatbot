import streamlit as st
import psycopg2
import pandas as pd
import google.generativeai as genai
import os
from dotenv import load_dotenv

# ----------- Load Environment Variables -----------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
# ----------- PostgreSQL Configuration -----------
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "123"

# ----------- Connect and run SQL query -----------
def read_sql_query(sql):
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()
        return rows, colnames
    except Exception as e:
        return [], [f"Error: {e}"]

# ----------- Fetch list of tables and columns from DB -----------
def get_table_schema():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position;
        """)
        schema_data = cur.fetchall()
        cur.close()
        conn.close()
        return schema_data
    except Exception as e:
        return [("Error", str(e))]

# ----------- Configure Google Gemini -----------
genai.configure(api_key=GEMINI_API_KEY)

# ----------- Generate SQL Query with Gemini -----------
def get_gemini_response(question, schema_prompt):
    try:
        model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest")
        full_prompt = f"""
You are an expert in converting English questions to SQL queries.
The PostgreSQL database contains the following tables and columns:

{schema_prompt}

Convert the following question into an accurate PostgreSQL query.
Return only the SQL query (no explanation, no markdown formatting):

Question: {question}
        """
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating SQL: {e}"

# ----------- Streamlit UI -----------
st.set_page_config(page_title="Natural Language to SQL with Gemini + PostgreSQL")
st.title("SQL ChatBot")

# Load table and column schema from DB
schema_data = get_table_schema()
schema_text = ""
if schema_data and "Error" not in schema_data[0]:
    current_table = ""
    for table, column in schema_data:
        if table != current_table:
            schema_text += f"\nTable: {table}\n"
            current_table = table
        schema_text += f"  - {column}\n"
    st.sidebar.title("📋 Tables & Columns")
    st.sidebar.text(schema_text)
else:
    st.sidebar.error("⚠️ Couldn't load table schema")

# User input
question = st.text_input("Type your question in English (e.g. 'Show all actors from the US'):")

if st.button("Get Answer"):
    if question:
        sql_query = get_gemini_response(question, schema_text)
        st.write(f"🧠 Generated SQL:\n`{sql_query}`")
        rows, columns = read_sql_query(sql_query)

        if rows and "Error" not in columns[0]:
            st.subheader("📊 Query Results")
            st.dataframe(pd.DataFrame(rows, columns=columns))
        else:
            st.error(columns[0])
