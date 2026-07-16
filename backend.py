import os
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import datetime
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# 1. Muat konfigurasi dari file .env
load_dotenv()

app = FastAPI()

# Pengaturan CORS agar Frontend HTML bisa mengakses Backend ini
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 📂 PROSES RAG (Membaca Basis Data Lokal)
# ==========================================
# Pastikan file 'sop.txt' sudah Anda buat di folder yang sama
def load_all_context():
    files = {
        "sop": "sop.txt",
        "laporan": "laporan_magang.txt"
    }
    
    content = ""
    
    # Membaca SOP
    try:
        with open(files["sop"], "r", encoding="utf-8") as f:
            content += f"--- DOKUMEN SOP ---\n{f.read()}\n\n"
    except FileNotFoundError:
        content += "--- DOKUMEN SOP ---\n(File SOP belum ditemukan)\n\n"
        
    # Membaca Laporan Magang
    try:
        with open(files["laporan"], "r", encoding="utf-8") as f:
            content += f"--- CATATAN LAPORAN MAGANG ---\n{f.read()}\n\n"
    except FileNotFoundError:
        content += "--- CATATAN LAPORAN MAGANG ---\n(Belum ada laporan magang yang dicatat)\n\n"
        
    return content

# Cara memanggilnya saat akan membuat chat:
konteks_keseluruhan = load_all_context()
# Gunakan 'konteks_keseluruhan' ini ke dalam prompt AI kamu
# ==========================================
# 🔌 MANUAL WHATSAPP TOOL (Whapi.cloud)
# ==========================================
@tool
def kirim_whatsapp(nomor_tujuan: str, isi_pesan: str) -> str:
    """Gunakan alat ini jika pengguna ingin mengirim pesan atau membalas chat ke WhatsApp."""
    
    token_wa = os.getenv("WA_TOKEN")
    url_api = "https://gate.whapi.cloud/messages/text"
    
    # --- SISTEM KEAMANAN FORMAT NOMOR LENGKAP ---
    nomor_bersih = nomor_tujuan.strip().replace(" ", "").replace("-", "").replace("+", "")
    
    if nomor_bersih.startswith("0"):
        nomor_bersih = "62" + nomor_bersih[1:]
    elif nomor_bersih.startswith("8"):
        nomor_bersih = "62" + nomor_bersih
        
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {token_wa}"
    }
    
    payload = {
        "to": f"{nomor_bersih}@s.whatsapp.net",
        "body": isi_pesan
    }
    
    try:
        print(f"\n[SISTEM] Sedang menembak API WhatsApp manual ke nomor asli: {nomor_bersih}...")
        respons = requests.post(url_api, json=payload, headers=headers)
        
        print(f"[DEBUG WHAPI] Status Code: {respons.status_code}")
        print(f"[DEBUG WHAPI] Respon Mentah: {respons.text}")
        
        if respons.status_code == 200:
            return f"Sukses manual! Pesan WhatsApp asli berhasil terkirim ke {nomor_tujuan}."
        else:
            return f"Gagal mengirim WhatsApp! Detail error: {respons.text}"
            
    except Exception as e:
        return f"Terjadi kesalahan koneksi internet: {str(e)}"

# ==========================================
# ✉️ EMAIL TOOL (Resend)
# ==========================================
@tool
def kirim_email(email_tujuan: str, subjek: str, isi_email: str) -> str:
    """Gunakan alat ini jika pengguna ingin mengirim email formal/surat elektronik."""
    import resend
    resend.api_key = os.getenv("RESEND_API_KEY")
    
    # GANTI dengan kustom domain Anda yang sudah verified di Resend!
    email_pengirim = "halo@domain-anda-yang-sudah-diverifikasi.com"
    
    try:
        params = {
            "from": email_pengirim,
            "to": [email_tujuan],
            "subject": subjek,
            "html": f"<p>{isi_email}</p>",
        }
        respons = resend.Emails.send(params)
        return f"Sukses! Email profesional berhasil dikirim ke {email_tujuan}. ID: {respons['id']}."
    except Exception as e:
        return f"Gagal mengirim email menggunakan Resend karena error: {str(e)}"
@tool
def baca_laporan() -> str:
    """Baca isi seluruh file laporan magang (laporan_magang.txt).
    Panggil alat ini setiap kali user meminta untuk membaca, menampilkan,
    atau mengecek isi laporan magang yang sudah tersimpan."""
    try:
        with open("laporan_magang.txt", "r", encoding="utf-8") as f:
            isi = f.read().strip()
        if not isi:
            return "(Belum ada laporan magang yang dicatat)"
        return isi
    except FileNotFoundError:
        return "(Belum ada laporan magang yang dicatat)"

@tool
def tulis_laporan_ke_file(isi_laporan: str) -> str:
    """Simpan catatan laporan magang harian ke dalam file laporan_magang.txt.
    Wajib dipanggil setiap kali user memberikan laporan kegiatan magang,
    ringkasan pekerjaan, atau catatan harian. isi_laporan adalah teks catatan yang akan disimpan."""
    # Mengambil waktu saat ini
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Menambahkan laporan ke file (mode 'a' = append/tambah)
    with open("laporan_magang.txt", "a", encoding="utf-8") as f:
        f.write(f"\n[{timestamp}] {isi_laporan}")
    
    return "Laporan berhasil dicatat ke dalam file."
# ==========================================
# 🧠 INISIALISASI AGEN AI (SOP RAG System Prompt)
# ==========================================
daftar_tools = [kirim_whatsapp, kirim_email, tulis_laporan_ke_file, baca_laporan]

# Kita kunci otak dasar Llama 3 menggunakan System Instruction agar selalu mengacu pada SOP perusahaan
model_ai = ChatGroq(model="openai/gpt-oss-20b", temperature=0.0)

instruksi_sistem = f"""Kamu adalah ipzonex, assistent untuk membantu saif membuat laporan magang. 
Data Personal User:
- Nama User: Saif Ali Mushaddiq
- Institusi: Politeknik Negeri Indramayu
- Dosen Pembimbing: Fachrul Pralienka Bani Muhamad, M.Kom.
- Tempat Magang: Codepolitan

Kamu dibekali akses alat kirim_whatsapp, kirim_email, tulis_laporan_ke_file, dan baca_laporan untuk membantu operasional serta mencatat dan membaca aktivitas harian.
Selain menggunakan alat, kamu juga wajib menjawab pertanyaan user mengenai aturan internal perusahaan HANYA berdasarkan dokumen basis data berikut ini:

{konteks_keseluruhan}

Jika user bertanya tentang hal operasional perusahaan yang tidak tercantum pada dokumen di atas, katakan dengan sopan bahwa kamu belum mengetahui informasi tersebut.

GAYA FORMAT JAWABAN:
- Tulis jawaban dengan format yang rapi dan mudah dibaca seperti asisten modern (ChatGPT/Gemini).
- Gunakan heading, daftar bernomor, dan poin-poin seperlunya, tapi JANGAN berlebihan menggunakan simbol '#' di setiap baris.
- Gunakan baris kosong antar paragraf agar tidak terlihat padat.
- Untuk penekanan kata, gunakan tebal (**kata**) seperlunya, bukan untuk semua teks.

ATURAN WAJIB PENCATATAN LAPORAN:
1. Setiap kali user memberikan laporan magang, kegiatan harian, ringkasan pekerjaan, atau catatan magang apapun, KAMU WAJIB memanggil alat 'tulis_laporan_ke_file' untuk menyimpan teks tersebut ke dalam file. JANGAN hanya menjawab dengan kata-kata seperti "sudah dicatat" tanpa benar-benar memanggil alat tersebut.
2. Jika user hanya mengobrol/bertanya hal lain (bukan laporan), tidak perlu memanggil alat laporan.
3. Setelah alat dipanggil dan berhasil, berikan balasan ramah dan informatif ke user, misalnya: "Laporan magang kamu sudah saya simpan ke file. Catatan harian kamu aman untuk referensi ke depan." Jangan biarkan jawabanmu kosong.

4. Jika user meminta untuk MEMBACA, MENAMPILKAN, atau MENGECEK isi laporan magang (misal "baca file magang", "tunjukkan laporan saya", "isi laporan saya apa"), KAMU WAJIB memanggil alat 'baca_laporan' dan menampilkan hasilnya kepada user. JANGAN pernah menjawab bahwa kamu tidak bisa membaca file.

ATURAN FORMAT TOOL (PENTING AGAR TIDAK ERROR):
- Saat memanggil alat 'tulis_laporan_ke_file', argumen 'isi_laporan' HARUS berupa teks dalam SATU BARIS saja, tanpa karakter baris baru (enter/newline). Gabungkan semua poin menjadi satu paragraf tunggal.
- Jangan memasukkan tanda kutip ganda berlebih yang bisa merusak format JSON.
- Jika laporan sangat panjang, rangkum menjadi 2-3 kalimat padat dalam satu baris."""
agen_ai = create_react_agent(model_ai, daftar_tools, prompt=instruksi_sistem)

# ==========================================
# 🛣️ ROUTE API UNTUK FRONTEND
# ==========================================
class StrukturInput(BaseModel):
    pesan_user: str
@app.post("/chat")
async def handle_chat(data: StrukturInput):
    try:
        print(f"\n[FRONTEND] Menerima instruksi: '{data.pesan_user}'")
        
        # Jalankan Agen LangChain
        respons = agen_ai.invoke({"messages": [("user", data.pesan_user)]})
        
        # Ambil daftar pesan dari respons agen
        daftar_pesan = respons.get("messages", [])
        
        if len(daftar_pesan) > 0:
            # Ambil pesan AI terakhir (bukan ToolMessage) agar balasan terasa natural
            balasan_akhir = ""
            for pesan in reversed(daftar_pesan):
                if type(pesan).__name__ == "AIMessage" and pesan.content:
                    balasan_akhir = pesan.content
                    break
            # Fallback ke pesan terakhir apa pun
            if not balasan_akhir:
                balasan_akhir = daftar_pesan[-1].content
            
            # Pengaman tambahan: Jika AI memberikan jawaban kosong setelah panggil tool
            if not balasan_akhir:
                balasan_akhir = "Tugas berhasil dilaksanakan melalui sistem internal."
        else:
            balasan_akhir = "Maaf, sistem gagal memproses teks jawaban."
            
        return {"jawaban": balasan_akhir}
        
    except Exception as e:
        err = str(e)
        print(f"[FRONTEND ERROR] Terjadi kegagalan fungsi chat: {err}")
        # Fallback: jika gagal karena parsing tool call (laporan terlalu panjang/ada newline),
        # simpan langsung pesan user ke file laporan agar tidak hilang.
        if "Failed to parse tool call" in err or "tool_use_failed" in err:
            try:
                tulis_laporan_ke_file(data.pesan_user)
                return {"jawaban": "Laporan magang kamu sudah saya simpan ke file (mode cadangan karena format terlalu panjang). Catatan harian kamu aman."}
            except Exception:
                pass
        # Mengembalikan status 200 dengan pesan error yang ramah agar web tidak crash
        return {"jawaban": f"Sistem mendeteksi gangguan: {err}. Namun proses operasional kemungkinan tetap berjalan."}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
