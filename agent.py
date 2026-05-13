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
