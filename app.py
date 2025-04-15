import streamlit as st
import psycopg2
import pandas as pd
import google.generativeai as genai

# ----------- Load Secrets from Streamlit Cloud ----------- 
GEMINI_API_KEY = st.secrets["GEMINI"]["API_KEY"]
DB_HOST = st.secrets["postgres"]["DB_HOST"]
DB_PORT = st.secrets["postgres"]["DB_PORT"]
DB_NAME = st.secrets["postgres"]["DB_NAME"]
DB_USER = st.secrets["postgres"]["DB_USER"]
DB_PASSWORD = st.secrets["postgres"]["DB_PASSWORD"]

# ----------- Configure Gemini ----------- 
genai.configure(api_key=GEMINI_API_KEY)

# ----------- Connect and Run SQL Query ----------- 
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

# ----------- Fetch Table Schema ----------- 
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

# ----------- Generate SQL with Gemini ----------- 
def get_gemini_response(question, schema_prompt):
    try:
        model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest")
        prompt = f"""
You are an expert at translating English questions to PostgreSQL queries.
Here are the tables and columns in the database:

{schema_prompt}

Convert this question into a valid SQL query:
Question: {question}
"""
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating SQL: {e}"

# ----------- Streamlit UI ----------- 
st.set_page_config(page_title="SQL ChatBot", layout="wide")
st.title("🧠 Natural Language to SQL ChatBot")

# Display Schema
schema_data = get_table_schema()
schema_text = ""
if schema_data and "Error" not in schema_data[0]:
    current_table = ""
    for table, column in schema_data:
        if table != current_table:
            schema_text += f"\nTable: {table}\n"
            current_table = table
        schema_text += f"  - {column}\n"
    st.sidebar.title("📋 Database Schema")
    st.sidebar.text(schema_text)
else:
    st.sidebar.error("⚠️ Couldn't load table schema.")

# User Input
question = st.text_input("Ask a question (e.g. 'List all users from India'):")

if st.button("Get Answer"):
    if question:
        sql_query = get_gemini_response(question, schema_text)
        if "Error" not in sql_query:
            st.code(sql_query, language="sql")
            rows, columns = read_sql_query(sql_query)
            if rows and "Error" not in columns[0]:
                st.subheader("📊 Query Results")
                st.dataframe(pd.DataFrame(rows, columns=columns))
            else:
                st.error(columns[0])
        else:
            st.error(sql_query)
