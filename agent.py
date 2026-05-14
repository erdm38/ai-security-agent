import os
from openai import OpenAI
from dotenv import load_dotenv

# .env dosyasından API anahtarını yükle
load_dotenv()

def create_security_agent():
    # 1. API Anahtarını al
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("HATA: Lütfen .env dosyasında NVIDIA_API_KEY bilginizi ayarlayın!")
        return

    # NVIDIA DeepSeek istemcisini başlat
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )

    # 2. Ajanın Kimliğini (System Prompt) Yükle
    try:
        with open("security-auditor.md", "r", encoding="utf-8") as file:
            system_prompt = file.read()
    except FileNotFoundError:
        print("HATA: security-auditor.md dosyası bulunamadı!")
        return

    print("🛡️ Security Agent (DeepSeek-V4-Pro) Başlatıldı! Çıkmak için 'q' veya 'quit' yazın.")
    print("-" * 50)

    # Geçmiş mesajları tutacağımız liste
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # 3. Sonsuz Sohbet Döngüsü
    while True:
        user_input = input("\nSiz: ")
        
        if user_input.lower() in ['q', 'quit', 'exit']:
            print("Görüşmek üzere!")
            break

        if not user_input.strip():
            continue

        # Dosya tarama komutu eklendi: /scan <dosya_adi_veya_klasor>
        if user_input.startswith("/scan "):
            path = user_input.split(" ", 1)[1]
            
            files_to_scan = []
            if os.path.isfile(path):
                files_to_scan.append(path)
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        # Gereksiz klasörleri atla (.git, venv, pycache vb.)
                        if ".git" in root or "venv" in root or "__pycache__" in root:
                            continue
                        files_to_scan.append(os.path.join(root, file))
            else:
                print(f"HATA: '{path}' adında bir dosya veya klasör bulunamadı!")
                continue

            if not files_to_scan:
                print("Taranacak dosya bulunamadı!")
                continue

            all_code_content = ""
            success_count = 0
            for file_path in files_to_scan:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        file_content = f.read()
                        all_code_content += f"\n\n--- Dosya: {file_path} ---\n```\n{file_content}\n```"
                        success_count += 1
                except Exception as e:
                    print(f"Uyarı: '{file_path}' okunamadı: {e}")
            
            if success_count == 0:
                print("Hiçbir dosya okunamadı!")
                continue

            # Kodu ajana sormak için promptu değiştir
            user_input = f"Lütfen aşağıdaki kod dosyalarını güvenlik açıklarına karşı incele ve bulgularını raporla:\n{all_code_content}"
            print(f"[{success_count} adet dosya okundu ve analiz için ajana gönderiliyor...]")
            
        messages.append({"role": "user", "content": user_input})

        try:
            print("\n🤖 Security Agent: ", end="", flush=True)
            
            # NVIDIA üzerinden DeepSeek modeline istek gönderiyoruz (Stream modunda)
            completion = client.chat.completions.create(
                model="deepseek-ai/deepseek-v4-pro",
                messages=messages,
                temperature=1,
                top_p=0.95,
                max_tokens=16384,
                extra_body={"chat_template_kwargs":{"thinking":False}},
                stream=True
            )

            # Akıştan gelen cevabı harf harf / kelime kelime ekrana yazdır ve biriktir
            agent_reply = ""
            for chunk in completion:
                if not getattr(chunk, "choices", None):
                    continue
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    print(content, end="", flush=True)
                    agent_reply += content
            
            print() # Cevap bitince bir alt satıra geç

            # Ajanın cevabını geçmişe ekle
            messages.append({"role": "assistant", "content": agent_reply})

        except Exception as e:
            print(f"\nBeklenmeyen bir hata oluştu: {e}")

if __name__ == "__main__":
    create_security_agent()
