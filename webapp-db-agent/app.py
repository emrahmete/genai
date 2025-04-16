from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import os
import json
from langchain_openai import AzureChatOpenAI
from langchain.agents import initialize_agent, Tool
from langchain_experimental.tools import PythonREPLTool
from langchain.memory import ConversationBufferMemory
import psycopg2
import pandas as pd
import re

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "database_connection_secret_key"  # Session için gerekli
CORS(app)

# Environment variables for Azure OpenAI
# Azure OpenAI configuration - varsayılan boş değerlerle
AZURE_OPENAI_DEPLOYMENT_NAME = ""
AZURE_OPENAI_ENDPOINT = ""
AZURE_OPENAI_API_KEY = ""
AZURE_OPENAI_API_VERSION = "2024-12-01-preview"  # Sadece varsayılan API sürümünü tutuyoruz

# Default database connection settings - varsayılan boş değerlerle
DB_CONFIG = {
    "host": "",
    "name": "",
    "user": "",
    "password": "",
    "port": 5432,  # Varsayılan PostgreSQL portu
    "sslmode": "require"
}

# Dosya yolunu tam olarak belirtelim
DB_CONNECTIONS_FILE = os.path.join(os.path.dirname(__file__), "db_connections.json")

# Dil modeli bağlantıları için kayıt dosyasını tanımla
LLM_MODELS_FILE = "llm_models.json"

# Varsayılan dil modeli yapılandırması
DEFAULT_LLM_CONFIG = {
    "deployment_name": AZURE_OPENAI_DEPLOYMENT_NAME,
    "endpoint": AZURE_OPENAI_ENDPOINT,
    "api_key": AZURE_OPENAI_API_KEY,
    "api_version": AZURE_OPENAI_API_VERSION,
    "temperature": 0.0
}

# Aktif dil modeli yapılandırması
LLM_CONFIG = DEFAULT_LLM_CONFIG.copy()

# Aktif dil modeli adını tutacak değişken
ACTIVE_MODEL_NAME = "Varsayılan"

# Dil modeli yapılandırmalarını yükle - Güncelleme
def load_llm_models():
    if os.path.exists(LLM_MODELS_FILE):
        try:
            with open(LLM_MODELS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

# Dil modeli yapılandırmalarını kaydet - Güncelleme
def save_llm_model(name, config, is_default=False):
    models = load_llm_models()
    
    # Yeni modeli is_default bilgisiyle kaydet
    models[name] = {
        "config": config,
        "is_default": is_default
    }
    
    # Eğer bu model varsayılan olarak işaretlendiyse, diğerlerini varsayılan olmaktan çıkar
    if is_default:
        for model_name in models:
            if model_name != name:
                if "is_default" in models[model_name]:
                    models[model_name]["is_default"] = False
    
    with open(LLM_MODELS_FILE, 'w') as f:
        json.dump(models, f)

# Uygulama başlangıcında varsayılan dil modelini yükle
def load_default_llm_model():
    global LLM_CONFIG
    global ACTIVE_MODEL_NAME
    
    models = load_llm_models()
    
    # Eğer hiç model tanımlanmamışsa varsayılan yapılandırmayı kaydet
    if not models:
        save_llm_model("Varsayılan", DEFAULT_LLM_CONFIG, is_default=True)
        models = load_llm_models()
    
    # Varsayılan olarak işaretlenmiş modeli bul
    default_model = None
    for name, data in models.items():
        # Hem eski format hem de yeni format kontrol edilir
        if isinstance(data, dict) and "is_default" in data and data.get("is_default"):
            config = data["config"]
            default_model = (name, config)
            break
    
    # Varsayılan işaretli model yoksa ilk modeli al
    if default_model is None and models:
        name = next(iter(models))
        data = models[name]
        # Eski format ve yeni format kontrol edilir
        config = data["config"] if isinstance(data, dict) and "config" in data else data
        default_model = (name, config)
    
    # Eğer bir model bulunduysa, onu aktif yap
    if default_model:
        ACTIVE_MODEL_NAME = default_model[0]
        LLM_CONFIG = default_model[1]
    
    return ACTIVE_MODEL_NAME

# Mevcut tanımlı dil modellerini yükle
LLM_MODELS = load_llm_models()

# İlk başlangıçta varsayılan modeli yükle
ACTIVE_MODEL_NAME = load_default_llm_model()

# Veritabanı bağlantılarını yükle - Debug eklenmiş
def load_db_connections():
    print(f"Loading DB connections from: {os.path.abspath(DB_CONNECTIONS_FILE)}")
    if os.path.exists(DB_CONNECTIONS_FILE):
        try:
            with open(DB_CONNECTIONS_FILE, 'r') as f:
                connections = json.load(f)
                print(f"Loaded connections: {connections.keys()}")
                return connections
        except Exception as e:
            print(f"Error loading connections: {str(e)}")
            return {}
    else:
        print("Connections file does not exist")
        return {}

# Veritabanı bağlantılarını kaydet - Güncelleme
def save_db_connection(name, config):
    connections = load_db_connections()
    connections[name] = config
    try:
        with open(DB_CONNECTIONS_FILE, 'w') as f:
            json.dump(connections, f)
        print(f"Saved connection '{name}' to {DB_CONNECTIONS_FILE}")
        return True
    except Exception as e:
        print(f"Error saving connection: {str(e)}")
        return False

# Uygulama başlangıcında çağırın
def initialize_connections_file():
    if os.path.exists(DB_CONNECTIONS_FILE):
        try:
            # Dosyayı açıp geçerli JSON olup olmadığını kontrol et
            with open(DB_CONNECTIONS_FILE, 'r') as f:
                json.load(f)
        except:
            # Geçersiz JSON dosyasını yeniden oluştur
            print(f"Invalid JSON file found. Recreating {DB_CONNECTIONS_FILE}")
            with open(DB_CONNECTIONS_FILE, 'w') as f:
                json.dump({}, f)
    else:
        # Dosya yoksa boş bir dosya oluştur
        with open(DB_CONNECTIONS_FILE, 'w') as f:
            json.dump({}, f)

# Test bağlantısı ekleme (geçici)
def add_test_connection():
    if not os.path.exists(DB_CONNECTIONS_FILE) or os.path.getsize(DB_CONNECTIONS_FILE) == 0:
        test_config = {
            "host": "test-server.database.com",
            "name": "test-db",
            "user": "test-user",
            "password": "test-password",
            "port": 5432,
            "sslmode": "require"
        }
        save_db_connection("Test Connection", test_config)
        print("Added test connection for debugging")

# Mevcut tanımlı bağlantıları yükle
DB_CONNECTIONS = load_db_connections()

# 1. Azure OpenAI ile LLM ayarları
def setup_openai_llm():
    return AzureChatOpenAI(
        deployment_name=LLM_CONFIG["deployment_name"],
        azure_endpoint=LLM_CONFIG["endpoint"],
        openai_api_version=LLM_CONFIG["api_version"],
        openai_api_key=LLM_CONFIG["api_key"],
        temperature=LLM_CONFIG["temperature"]
    )

# 2. PostgreSQL (Azure Cosmos ile bağlantı)
def setup_postgresql_connection():
    connection = psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        database=DB_CONFIG["name"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        sslmode=DB_CONFIG["sslmode"]
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

# Formatlanmış sonuçlar için yardımcı fonksiyon
def format_dataframe_to_html(df):
    # HTML formatında tablo döndür
    return df.to_html(classes='table table-striped table-hover table-sm', index=False)

# 4. Tool(s) Tanımı - Tablo Metadata'sı ve Query Aracı
def get_table_metadata(_=None):
    query = """
    SELECT table_schema, table_name, column_name, data_type 
    FROM information_schema.columns 
    where information_schema."columns".table_schema = 'public'
    ORDER BY table_schema, table_name;
    """
    df = execute_sql_query(query)
    return format_dataframe_to_html(df)

# SQL Sorgulama Aracı
def sql_query_tool(query):
    df = execute_sql_query(query)
    # Tablo formatında HTML döndür
    return format_dataframe_to_html(df)

def get_current_datetime(_=None):
    from datetime import datetime
    current_time = datetime.now()
    return current_time.strftime("%Y-%m-%d %H:%M:%S")

# Create agent with memory
def create_agent():
    # Yapılandırma kontrolü
    if not (AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY and AZURE_OPENAI_DEPLOYMENT_NAME):
        print("WARNING: Azure OpenAI yapılandırması eksik!")
        # Ya varsayılan bir agent döndürün ya da None
    
    if not (DB_CONFIG["host"] and DB_CONFIG["name"] and DB_CONFIG["user"] and DB_CONFIG["password"]):
        print("WARNING: Database yapılandırması eksik!")
        # Ya varsayılan bir agent döndürün ya da None
    
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
    5. Format query results will be automatically formatted as HTML tables
    6. If the user query the database, use the Execute SQL Query tool and return the results. SQL Query should be valid and optimized for PostgreSQL.
    7. If the user asks for the current date and time, use the Get Current DateTime tool.
    8. For listed information, ALWAYS use proper formatting with Markdown:
       - Use bullet points with hyphens (-)
       - Keep each list item on a separate line
       - Use line breaks between paragraphs
       - Use HTML <br> tags for explicit line breaks
       - Format SQL queries with proper indentation
    9. DO NOT use commas or semicolons to separate list items horizontally - always use vertical lists
    10. When showing multiple options or items, ALWAYS format them as a vertical list, never in a horizontal line
    
    You are an expert in PostgreSQL and SQL query optimization. Your task is to generate a **valid and optimized SQL query** based on the user's request...
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
    # Bağlantı ayarları kontrol edilir
    llm_config_valid = bool(LLM_CONFIG.get("endpoint") and LLM_CONFIG.get("api_key") and LLM_CONFIG.get("deployment_name"))
    db_config_valid = bool(DB_CONFIG.get("host") and DB_CONFIG.get("name") and DB_CONFIG.get("user") and DB_CONFIG.get("password"))
    
    return render_template('index.html', 
                          llm_config_valid=llm_config_valid, 
                          db_config_valid=db_config_valid)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    
    try:
        # Agent'ı çağır (Lazy loading kullanılıyorsa get_agent() ile)
        # agent = get_agent() 
        response = agent.run(user_message) # Agent'ın çalıştığını varsayıyoruz
        
        # --- Yanıt Formatlama Başlangıcı ---
        
        # 1. Markdown tarzı listeleri (-, *, 1.) HTML listelerine çevir
        formatted_response = ""
        in_list = False
        list_type = None # 'ul' or 'ol'
        
        lines = response.strip().split('\n')
        processed_lines = []

        for line in lines:
            line = line.strip()
            
            # Markdown listesi başlangıcı kontrolü
            ul_match = re.match(r'^[-*]\s+(.*)', line)
            ol_match = re.match(r'^\d+\.\s+(.*)', line)

            if ul_match:
                item_content = ul_match.group(1).strip()
                if not in_list or list_type != 'ul':
                    if in_list: # Önceki listeyi kapat
                        processed_lines.append(f'</{list_type}>')
                    processed_lines.append('<ul>')
                    in_list = True
                    list_type = 'ul'
                processed_lines.append(f'<li>{item_content}</li>')
            elif ol_match:
                item_content = ol_match.group(1).strip()
                if not in_list or list_type != 'ol':
                    if in_list: # Önceki listeyi kapat
                        processed_lines.append(f'</{list_type}>')
                    processed_lines.append('<ol>')
                    in_list = True
                    list_type = 'ol'
                processed_lines.append(f'<li>{item_content}</li>')
            else:
                # Liste bittiyse kapat
                if in_list:
                    processed_lines.append(f'</{list_type}>')
                    in_list = False
                
                # Normal satırları <p> içine alabiliriz (isteğe bağlı)
                if line: # Boş satırları atla
                   processed_lines.append(f'<p>{line}</p>')

        # Döngü bittiğinde açık liste varsa kapat
        if in_list:
            processed_lines.append(f'</{list_type}>')
            
        formatted_response = "".join(processed_lines)

        # 2. Virgül/Noktalı virgül ile ayrılmış yatay listeleri dikey yap (Ekstra kontrol)
        # Bu kısım çok agresif olabilir, gerekirse kaldırın veya düzenleyin
        # formatted_response = formatted_response.replace(', ', '<br>- ')
        # formatted_response = formatted_response.replace('; ', '<br>- ')

        # 3. Satır sonlarını <br> ile değiştir (Paragraflar arası boşluk için)
        # formatted_response = formatted_response.replace('\n', '<br>') # <p> kullandığımız için buna gerek kalmayabilir

        # --- Yanıt Formatlama Sonu ---

        return jsonify({"response": formatted_response})
        
    except Exception as e:
        print(f"Chat Error: {str(e)}") # Hata loglamayı iyileştir
        return jsonify({"error": str(e)}), 500

@app.route('/api/clear_chat', methods=['POST'])
def clear_chat():
    global agent
    # Yeni bir agent oluşturarak hafızayı sıfırla
    agent = create_agent()
    return jsonify({"status": "success", "message": "Chat history cleared"})

@app.route('/api/connect_database', methods=['POST'])
def connect_database():
    try:
        data = request.json
        
        # Yeni bağlantı bilgilerini al
        global DB_CONFIG
        DB_CONFIG = {
            "host": data.get('host'),
            "name": data.get('name'),
            "user": data.get('user'),
            "password": data.get('password'),
            "port": int(data.get('port', 5432)),
            "sslmode": data.get('sslmode', 'require')
        }
        
        # Bağlantıyı test et
        connection = setup_postgresql_connection()
        connection.close()
        
        # Bağlantı başarılı olursa, agent'ı yeniden başlat
        global agent
        agent = create_agent()
        
        return jsonify({"status": "success", "message": "Database connection successful"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# API endpoint: Kayıtlı bağlantıları listele - Debug eklenmiş
@app.route('/api/db_connections', methods=['GET'])
def get_db_connections():
    global DB_CONNECTIONS
    # Dosyadan yeniden yükle ki dosya manuel değiştiyse de görelim
    DB_CONNECTIONS = load_db_connections()
    connections_list = list(DB_CONNECTIONS.keys())
    print(f"Serving connections list: {connections_list}")
    return jsonify({"connections": connections_list})

# API endpoint: Bağlantı bilgilerini kaydet
@app.route('/api/save_connection', methods=['POST'])
def save_connection():
    try:
        global DB_CONFIG
        
        data = request.json
        connection_name = data.get('name')
        
        # Eksik veri kontrolü ekleyin
        if not connection_name:
            return jsonify({"status": "error", "message": "Connection name is required"}), 400
        
        # Geçici değişkeni try bloğunun başında tanımlayın
        temp_config = DB_CONFIG.copy()
        
        connection_config = {
            "host": data.get('host'),
            "name": data.get('dbName'),
            "user": data.get('user'),
            "password": data.get('password'),
            "port": int(data.get('port', 5432)),
            "sslmode": data.get('sslmode', 'require')
        }
        
        # Bağlantıyı test et
        DB_CONFIG = connection_config
        connection = setup_postgresql_connection()
        connection.close()
        
        # Bağlantı başarılı ise kaydet
        save_db_connection(connection_name, connection_config)
        global DB_CONNECTIONS
        DB_CONNECTIONS = load_db_connections()
        
        return jsonify({"status": "success", "message": "Connection saved successfully"})
    except Exception as e:
        # Hata durumunda orijinal config'e dön (eğer temp_config tanımlandıysa)
        if 'temp_config' in locals():
            DB_CONFIG = temp_config
        return jsonify({"status": "error", "message": str(e)}), 500

# API endpoint: Kaydedilmiş bağlantıyı yükle
@app.route('/api/load_connection', methods=['POST'])
def load_connection():
    try:
        global DB_CONFIG  # Global tanımlamasını fonksiyonun başına taşıyın
        global agent      # Bu da önemli
        
        data = request.json
        connection_name = data.get('name')
        
        if connection_name not in DB_CONNECTIONS:
            return jsonify({"status": "error", "message": "Connection not found"}), 404
        
        # Bağlantı bilgilerini yükle
        DB_CONFIG = DB_CONNECTIONS[connection_name]
        
        # Test et
        connection = setup_postgresql_connection()
        connection.close()
        
        # Agent'ı yeniden başlat
        agent = create_agent()
        
        return jsonify({"status": "success", "message": "Connection loaded successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# API endpoint: Kayıtlı dil modellerini listele
@app.route('/api/llm_models', methods=['GET'])
def get_llm_models():
    return jsonify({"models": list(LLM_MODELS.keys())})

# API endpoint: Dil modeli bilgilerini kaydet - Güncelleme
@app.route('/api/save_llm_model', methods=['POST'])
def save_llm_model_endpoint():
    try:
        global LLM_CONFIG
        global LLM_MODELS  # Global tanımlamasını fonksiyonun başına taşıdık
        global ACTIVE_MODEL_NAME  # Bunu da ekledik
        
        data = request.json
        model_name = data.get('name')
        is_default = data.get('is_default', False)
        
        # Eksik veri kontrolü
        if not model_name:
            return jsonify({"status": "error", "message": "Model name is required"}), 400
        
        # Geçici değişkeni try bloğunun başında tanımlayın
        temp_config = LLM_CONFIG.copy()
        
        model_config = {
            "deployment_name": data.get('deployment_name'),
            "endpoint": data.get('endpoint'),
            "api_key": data.get('api_key'),
            "api_version": data.get('api_version'),
            "temperature": float(data.get('temperature', 0.0))
        }
        
        try:
            # Modeli test et
            LLM_CONFIG = model_config
            test_llm = setup_openai_llm()
            
            # Basit bir test mesajı göndererek hata kontrolü yap
            test_llm.invoke("Hello, are you working?")
            
            # Model başarılı ise kaydet
            save_llm_model(model_name, model_config, is_default)
            LLM_MODELS = load_llm_models()  # Global tanımlamayı yukarıya taşıdık
            
            # Eğer varsayılan olarak işaretlendiyse, aktif model olarak da ayarla
            if is_default:
                ACTIVE_MODEL_NAME = model_name  # Global tanımlamayı yukarıya taşıdık
            
            return jsonify({"status": "success", "message": "Model saved successfully"})
        except Exception as test_error:
            # Test sırasında hata oluştu, orijinal config'e dön
            LLM_CONFIG = temp_config
            return jsonify({"status": "error", "message": f"Model test failed: {str(test_error)}"}), 500
            
    except Exception as e:
        # Genel hata durumunda orijinal config'e dön
        if 'temp_config' in locals():
            LLM_CONFIG = temp_config
        return jsonify({"status": "error", "message": str(e)}), 500

# API endpoint: Kaydedilmiş dil modelini yükle - Güncelleme
@app.route('/api/load_llm_model', methods=['POST'])
def load_llm_model():
    try:
        global LLM_CONFIG
        global agent
        global ACTIVE_MODEL_NAME
        global LLM_MODELS  # Bu satır eksikti - global tanımlaması eklendi
        
        data = request.json
        model_name = data.get('name')
        set_as_default = data.get('set_as_default', False)
        
        if model_name not in LLM_MODELS:
            return jsonify({"status": "error", "message": "Model not found"}), 404
        
        # Model bilgilerini yükle - Hem eski hem de yeni format için kontrol
        model_data = LLM_MODELS[model_name]
        LLM_CONFIG = model_data["config"] if isinstance(model_data, dict) and "config" in model_data else model_data
        
        # Eğer varsayılan olarak ayarlanması istendiyse
        if set_as_default:
            save_llm_model(model_name, LLM_CONFIG, is_default=True)
            LLM_MODELS = load_llm_models()
        
        # Aktif model adını güncelle
        ACTIVE_MODEL_NAME = model_name
        
        # Agent'ı yeniden başlat
        agent = create_agent()
        
        return jsonify({"status": "success", "message": "Model loaded successfully"})
    except Exception as e:
        print(f"Load model error: {str(e)}")  # Debug için log ekleyin
        return jsonify({"status": "error", "message": str(e)}), 500

# Aktif model bilgisini döndüren yeni endpoint
@app.route('/api/active_model', methods=['GET'])
def get_active_model():
    return jsonify({"name": ACTIVE_MODEL_NAME})

# Yapılandırma durumunu kontrol eden API endpoint
@app.route('/api/config_status', methods=['GET'])
def config_status():
    llm_config_valid = bool(LLM_CONFIG.get("endpoint") and LLM_CONFIG.get("api_key") and LLM_CONFIG.get("deployment_name"))
    db_config_valid = bool(DB_CONFIG.get("host") and DB_CONFIG.get("name") and DB_CONFIG.get("user") and DB_CONFIG.get("password"))
    
    return jsonify({
        "llm_config_valid": llm_config_valid,
        "db_config_valid": db_config_valid
    })

if __name__ == '__main__':
    initialize_connections_file()
    add_test_connection()  # Test için
    agent = create_agent()
    app.run(debug=True)