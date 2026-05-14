import os

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma
    from langchain_core.documents import Document
except ImportError:
    raise ImportError("RAG kütüphaneleri eksik. Lütfen 'pip install chromadb langchain langchain-community langchain-huggingface sentence-transformers' komutunu çalıştırın.")

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")

def get_embeddings_model():
    # Lokal ve ücretsiz bir embedding modeli kullanıyoruz. (İnternetsiz çalışabilir, API anahtarı istemez)
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def build_index(directory_path):
    documents = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if any(ignore_dir in root for ignore_dir in [".git", "venv", "__pycache__", "node_modules", "chroma_db"]):
                continue
            
            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Boş dosyaları atla
                    if content.strip():
                        documents.append(Document(page_content=content, metadata={"source": file_path}))
            except Exception:
                pass # İkili (binary) veya okunamayan dosyaları atla

    if not documents:
        return "HATA: Okunabilir metin dosyası bulunamadı veya klasör boş."

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(documents)

    # ChromaDB'ye kaydet
    vectorstore = Chroma.from_documents(documents=splits, embedding=get_embeddings_model(), persist_directory=DB_DIR)
    return f"✅ Başarıyla indexlendi: {len(documents)} dosya okundu, {len(splits)} parçaya bölündü ve RAG veritabanına kaydedildi."

def search_codebase(query, k=5):
    if not os.path.exists(DB_DIR):
        return "HATA: Henüz hiçbir proje indexlenmemiş. Vektör veritabanı boş."
    
    try:
        vectorstore = Chroma(persist_directory=DB_DIR, embedding=get_embeddings_model())
        results = vectorstore.similarity_search(query, k=k)
        
        if not results:
            return "Sonuç bulunamadı."
            
        response = ""
        for i, doc in enumerate(results):
            response += f"\n--- Eşleşme {i+1} (Dosya: {doc.metadata.get('source', 'Bilinmiyor')}) ---\n"
            response += doc.page_content + "\n"
            
        return response
    except Exception as e:
        return f"Arama sırasında bir hata oluştu: {str(e)}"
