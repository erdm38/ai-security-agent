import os
import json
from openai import OpenAI
from dotenv import load_dotenv
import rag_engine

# .env dosyasından API anahtarını yükle
load_dotenv()

# Dizin Yolları
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCAN_DIR = os.path.join(BASE_DIR, "security-scanning")
AGENTS_DIR = os.path.join(SCAN_DIR, "agents")
SKILLS_DIR = os.path.join(SCAN_DIR, "skills")
COMMANDS_DIR = os.path.join(SCAN_DIR, "commands")

def get_file_content(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return str(e)

# --- ARAÇLAR (TOOLS) ---
def list_available_resources():
    agents = [f.replace('.md', '') for f in os.listdir(AGENTS_DIR) if f.endswith('.md')] if os.path.exists(AGENTS_DIR) else []
    skills = [f for f in os.listdir(SKILLS_DIR) if os.path.isdir(os.path.join(SKILLS_DIR, f))] if os.path.exists(SKILLS_DIR) else []
    commands = [f.replace('.md', '') for f in os.listdir(COMMANDS_DIR) if f.endswith('.md')] if os.path.exists(COMMANDS_DIR) else []
    
    return json.dumps({
        "agents": agents,
        "skills": skills,
        "commands": commands
    })

def change_persona(agent_name):
    filepath = os.path.join(AGENTS_DIR, f"{agent_name}.md")
    if os.path.exists(filepath):
        content = get_file_content(filepath)
        print(f"\n[🛠️ Sistem: Ajan rolü '{agent_name}' olarak değiştirildi.]")
        return json.dumps({"status": "success", "message": f"Persona changed to {agent_name}", "content": content})
    return json.dumps({"status": "error", "message": f"Agent {agent_name} not found."})

def load_skill(skill_name):
    filepath = os.path.join(SKILLS_DIR, skill_name, "SKILL.md")
    if os.path.exists(filepath):
        content = get_file_content(filepath)
        print(f"\n[🛠️ Sistem: '{skill_name}' yeteneği (skill) hafızaya yüklendi.]")
        return json.dumps({"status": "success", "message": f"Skill {skill_name} loaded", "content": content})
    return json.dumps({"status": "error", "message": f"Skill {skill_name} not found."})

def get_command_template(command_name):
    filepath = os.path.join(COMMANDS_DIR, f"{command_name}.md")
    if os.path.exists(filepath):
        content = get_file_content(filepath)
        print(f"\n[🛠️ Sistem: '{command_name}' komut şablonu arka planda okundu.]")
        return json.dumps({"status": "success", "message": f"Command {command_name} loaded", "content": content})
    return json.dumps({"status": "error", "message": f"Command {command_name} not found."})

# --- JSON SCHEMA ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "list_available_resources",
            "description": "Returns a list of all available agent personas, skills, and command templates in the project directory.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "change_persona",
            "description": "Changes the core persona/system prompt of the agent. Use this when the user asks you to act as a different expert (e.g., threat-modeling-expert).",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string", "description": "The name of the agent to load without the .md extension"}
                },
                "required": ["agent_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "load_skill",
            "description": "Loads a specific skill into your context. Use this when you need specialized knowledge to fulfill a user request (e.g., sast-configuration).",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "The directory name of the skill to load"}
                },
                "required": ["skill_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_command_template",
            "description": "Loads a command execution template. Use this when the user asks to run a specific scan or hardening task (e.g., security-sast).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command_name": {"type": "string", "description": "The name of the command template without the .md extension"}
                },
                "required": ["command_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_codebase",
            "description": "Searches the locally indexed codebase using RAG (Vector Database) for semantic matches to a query. Use this when you need to find relevant code snippets (e.g., 'auth mechanisms', 'SQL queries', 'JWT validation') across a large project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query, e.g., 'database connection' or 'jwt token validation'"},
                    "k": {"type": "integer", "description": "Number of code chunks to return. Default is 5."}
                },
                "required": ["query"]
            }
        }
    }
]

def create_security_agent():
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("HATA: Lütfen .env dosyasında NVIDIA_API_KEY bilginizi ayarlayın!")
        return

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )

    # Başlangıç sistem promptunu oku
    initial_agent = "security-auditor"
    filepath = os.path.join(AGENTS_DIR, f"{initial_agent}.md")
    
    # Eger ajan dosyası agents klasöründe yoksa kök dizindeki fallback dosyasını dene (eski yapı için)
    if not os.path.exists(filepath):
        filepath = os.path.join(BASE_DIR, f"{initial_agent}.md")

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            system_prompt = file.read()
    except FileNotFoundError:
        print(f"HATA: {initial_agent}.md dosyası bulunamadı!")
        return

    print("🛡️ Security Agent (Tool-Calling Mimari) Başlatıldı! Çıkmak için 'q' veya 'quit' yazın.")
    print("İpucu: 'Bana yeteneklerini listele', 'Tehdit modelleme uzmanı ol' veya 'SAST taraması şablonunu yükle' diyebilirsiniz.")
    print("-" * 50)

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    while True:
        user_input = input("\nSiz: ")
        
        if user_input.lower() in ['q', 'quit', 'exit']:
            print("Görüşmek üzere!")
            break

        if not user_input.strip():
            continue

        if user_input.startswith("/index "):
            path = user_input.split(" ", 1)[1]
            if os.path.isdir(path):
                print(f"[{path} klasörü vektör veritabanına ekleniyor. Bu işlem proje boyutuna göre sürebilir...]")
                try:
                    result_msg = rag_engine.build_index(path)
                    print(result_msg)
                except Exception as e:
                    print(f"Indexleme hatası: {e}")
            else:
                print(f"HATA: '{path}' adında geçerli bir klasör bulunamadı!")
            continue

        # Klasik /scan komutu desteği (geriye dönük uyumluluk için)
        if user_input.startswith("/scan "):
            path = user_input.split(" ", 1)[1]
            files_to_scan = []
            if os.path.isfile(path):
                files_to_scan.append(path)
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        if ".git" in root or "venv" in root or "__pycache__" in root:
                            continue
                        files_to_scan.append(os.path.join(root, file))
            else:
                print(f"HATA: '{path}' adında bir dosya veya klasör bulunamadı!")
                continue

            if files_to_scan:
                all_code_content = ""
                for file_path in files_to_scan:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            all_code_content += f"\n\n--- Dosya: {file_path} ---\n```\n{f.read()}\n```"
                    except Exception:
                        pass
                user_input = f"Lütfen aşağıdaki kod dosyalarını güvenlik açıklarına karşı incele:\n{all_code_content}"
                print(f"[{len(files_to_scan)} adet dosya analiz için ajana gönderiliyor...]")

        messages.append({"role": "user", "content": user_input})

        # Tool Calling ve Cevap Döngüsü
        while True:
            try:
                # Tool calling kullanırken stream kullanmak parsing açısından karmaşıktır.
                # Bu yüzden burada stream=False kullanıyoruz.
                response = client.chat.completions.create(
                    model="minimaxai/minimax-m2.7",
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=1,
                    top_p=0.95,
                    max_tokens=8192,
                    stream=False
                )
                
                response_message = response.choices[0].message
                
                # Model bir araç (tool) kullanmaya karar verdiyse
                if response_message.tool_calls:
                    # Tool call isteğini geçmişe ekle
                    messages.append(response_message)
                    
                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        function_response = ""
                        
                        # Hangi fonksiyon istendiyse onu çalıştır
                        if function_name == "list_available_resources":
                            function_response = list_available_resources()
                        elif function_name == "change_persona":
                            agent_name = function_args.get("agent_name")
                            res_json = change_persona(agent_name)
                            res = json.loads(res_json)
                            function_response = res_json
                            
                            # Eger sistem promptunu degistirdiysek, geçmişteki ilk mesaji güncelleyelim
                            if res.get("status") == "success":
                                if messages and messages[0]["role"] == "system":
                                    messages[0]["content"] = res["content"]
                                    
                        elif function_name == "load_skill":
                            function_response = load_skill(function_args.get("skill_name"))
                        elif function_name == "get_command_template":
                            function_response = get_command_template(function_args.get("command_name"))
                        elif function_name == "search_codebase":
                            query = function_args.get("query")
                            k = function_args.get("k", 5)
                            print(f"\n[🛠️ Sistem: Vektör DB'de kod aranıyor: '{query}']")
                            function_response = rag_engine.search_codebase(query, k)
                        
                        # Fonksiyonun döndürdüğü cevabı "tool" rolüyle geçmişe ekle
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_response,
                        })
                    
                    # Araç işlemleri bitti, while döngüsü başa dönecek ve 
                    # araçtan gelen cevaplarla modeli tekrar çağırarak son metin cevabını üretecek.
                    continue
                else:
                    # Model normal bir metin cevabı ürettiyse, döngüyü kırıp ekrana bas
                    agent_reply = response_message.content
                    print("\n🤖 Security Agent:\n", agent_reply)
                    messages.append({"role": "assistant", "content": agent_reply})
                    break

            except Exception as e:
                print(f"\nBeklenmeyen bir hata oluştu (API veya Tool): {e}")
                break

if __name__ == "__main__":
    create_security_agent()
