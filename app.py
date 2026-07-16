import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 1. Muat API Key dari .env
load_dotenv()

# 2. Siapkan komponen Rantai AI
prompt_template = ChatPromptTemplate.from_messages([
    ("system", "Kamu adalah asisten AI yang ahli memberikan analogi pemrograman."),
    ("human", "Jelaskan konsep tentang {topik} dengan analogi dunia nyata.")
])

# Daftar model Groq gratis sebagai fallback
DAFTAR_MODEL = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
    "llama-3.2-3b-preview",
]

pembersih_output = StrOutputParser()

# 1. Minta input langsung dari pengguna di terminal
topik_pilihan = input("Masukkan topik pemrograman yang ingin Anda tanyakan: ")

print("\nSedang menghubungi Groq Cloud...\n")

# 2. Coba setiap model sebagai fallback jika sebelumnya gagal
hasil = None
for nama_model in DAFTAR_MODEL:
    try:
        model_ai = ChatGroq(model=nama_model, temperature=0.7)
        rantai_ai = prompt_template | model_ai | pembersih_output
        hasil = rantai_ai.invoke({"topik": topik_pilihan})
        print(f"[INFO] Berhasil menggunakan model: {nama_model}")
        break
    except Exception as e:
        print(f"[PERINGATAN] Model {nama_model} gagal: {e}. Mencoba model berikutnya...")
        continue

if hasil is None:
    print("Semua model Groq gagal dihubungi. Periksa koneksi atau API key Anda.")

print("=== JAWABAN AI ===")
print(hasil)

