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

# Menggunakan Groq dengan model Llama 3
model_ai = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)
pembersih_output = StrOutputParser()

# 3. Sambungkan komponen
rantai_ai = prompt_template | model_ai | pembersih_output

# Ganti baris kode invoke lama dengan baris di bawah ini:

# 1. Minta input langsung dari pengguna di terminal
topik_pilihan = input("Masukkan topik pemrograman yang ingin Anda tanyakan: ")

print("\nSedang menghubungi Groq Cloud...\n")

# 2. Masukkan variabel dari input terminal ke dalam rantai AI
hasil = rantai_ai.invoke({"topik": topik_pilihan})

print("=== JAWABAN AI ===")
print(hasil)

