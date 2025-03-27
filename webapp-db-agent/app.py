from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
from langchain_openai import AzureChatOpenAI
from langchain.agents import initialize_agent, Tool
from langchain_experimental.tools import PythonREPLTool
from langchain.memory import ConversationBufferMemory
import psycopg2
import pandas as pd

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Environment variables for Azure OpenAI
# Azure OpenAI configuration
AZURE_OPENAI_DEPLOYMENT_NAME = ""
AZURE_OPENAI_ENDPOINT = ""
AZURE_OPENAI_API_KEY = ""
AZURE_OPENAI_API_VERSION = ""

# Azure Cosmos PostgreSQL configuration
DB_HOST = ""
DB_NAME = ""
DB_USER = ""
DB_PASSWORD = ""
DB_PORT = 
SSL_MODE = ""

# 1. Azure OpenAI ile LLM ayarları
def setup_openai_llm():
    return AzureChatOpenAI(
        deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        openai_api_version=AZURE_OPENAI_API_VERSION,
        openai_api_key=AZURE_OPENAI_API_KEY,
        temperature=0.0
    )

# 2. PostgreSQL (Azure Cosmos ile bağlantı)
def setup_postgresql_connection():
    connection = psycopg2.connect(
        host="your_postgres_host",
        port="your_postgres_port",
        database="your_database_name",
        user="your_username",
        password="your_password",
        sslmode="require"
    )
    return connection

# 3. SQL Sorgu Tool'u
def execute_sql_query(sql_query: str):
    connection = setup_postgresql_connection()
    try:
        # SQL sorgusunu çalıştır
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            # Sonuçları Pandas DataFrame formatına çevir
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            df = pd.DataFrame(rows, columns=columns)
    finally:
        connection.close()

    return df

# 4. Tool(s) Tanımı - Tablo Metadata'sı ve Query Aracı
def get_table_metadata(_=None):
    query = """
    SELECT table_schema, table_name, column_name, data_type 
    FROM information_schema.columns 
    where information_schema."columns".table_schema = 'public'
    ORDER BY table_schema, table_name;
    """
    df = execute_sql_query(query)
    return df.to_string()

# SQL Sorgulama Aracı
def sql_query_tool(query):
    df = execute_sql_query(query)
    return df.to_string()

def get_current_datetime(_=None):
    from datetime import datetime
    current_time = datetime.now()
    return current_time.strftime("%Y-%m-%d %H:%M:%S")

# Create agent with memory
def create_agent():
    llm = setup_openai_llm()
    
    tools = [
        Tool(
            name="Query Database Metadata",
            func=get_table_metadata,
            description="Use this to get information about tables, columns, and their metadata."
        ),
        Tool(
            name="Execute SQL Query",
            func=sql_query_tool,
            description="Use this to run SQL queries on the database directly. If the query is not valid, you should fix the query and try again."
        ),
        Tool(
            name="Get Current DateTime",
            func=get_current_datetime,
            description="Use this to get the current date and time."
        ),
        PythonREPLTool()
    ]
    
    #memory limit by token
    memory = ConversationBufferMemory(memory_key="chat_history",return_messages=True, max_token_limit=5000)

    system_message = """You are a helpful SQL assistant specialized in querying PostgreSQL databases.
    
    Follow these instructions:
    0. Do not use this ` character in your response when you generate SQL queries : `
    1. When asked about database structure, always use the Query Database Metadata tool first
    2. Write clean, optimized SQL queries
    3. Explain your reasoning before executing queries
    4. If you get an error in a query, explain what went wrong and fix it
    5. Format query results in a readable way
    6. If the user query the database, use the Execute SQL Query tool and return the results. SQL Query should be valid and optimized for PostgreSQL.
    7. If the user asks for the current date and time, use the Get Current DateTime tool.  
    
    You are an expert in PostgreSQL and SQL query optimization. Your task is to generate a **valid and optimized SQL query** based on the user's request. Follow these rules strictly:  

    1. **Only return the SQL query** and nothing else. Do not include explanations, formatting, or unnecessary text.  
    2. **Ensure the query is 100% syntactically correct** and optimized for PostgreSQL.  
    3. Use **fully qualified table and column names** if necessary.  
    4. If a `WHERE` clause is needed, always ensure it **prevents full table scans** by using indexed columns when possible.  
    5. If a `JOIN` is required, use the most efficient type (`INNER JOIN`, `LEFT JOIN`, etc.) and **avoid Cartesian joins**.  
    6. If an `ORDER BY` clause is needed, **order only by indexed columns** when possible to enhance performance.  
    7. If using `LIMIT`, ensure it makes sense for pagination or performance tuning.  
    8. If an aggregation is needed (`COUNT`, `SUM`, `AVG`, etc.), group the results appropriately with `GROUP BY`.  
    9. Always escape user input properly to prevent SQL injection vulnerabilities.  

    ### **Example Queries:**  
    #### ✅ **Correct Query:**  
    SELECT product_name, unit_price  
    FROM products  
    WHERE category = 'Electronics'  
    ORDER BY unit_price DESC  
    LIMIT 10;
    
    #### ❌ **Incorrect Query:**  
    ```sql
    SELECT product_name, unit_price  
    FROM products  
    WHERE category = 'Electronics'  
    ORDER BY unit_price DESC  
    LIMIT 10;
    
    """
    
    agent = initialize_agent(
        tools,
        llm,
        agent="conversational-react-description",
        memory=memory,
        thought_chain_kwargs={"verbose": True},
        agent_type="chat-conversational-react-description",
        handle_parsing_errors=True,
        verbose=True,
            agent_kwargs={
            "system_message": system_message
        }
    )
    
    return agent

# Global agent instance
agent = create_agent()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    
    try:
        response = agent.run(user_message)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Yeni endpoint: Clear Chat
@app.route('/api/clear_chat', methods=['POST'])
def clear_chat():
    global agent
    # Yeni bir agent oluşturarak hafızayı sıfırla
    agent = create_agent()
    return jsonify({"status": "success", "message": "Chat history cleared"})

if __name__ == '__main__':
    app.run(debug=True)