import os
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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

    # Bersihkan artefak markdown agar tersimpan rapi
    teks_bersih = isi_laporan.replace("**", "").replace("`", "").strip()

    # Menambahkan laporan ke file (mode 'a' = append/tambah) dengan format rapi
    with open("laporan_magang.txt", "a", encoding="utf-8") as f:
        f.write(f"\n[{timestamp}]\n{teks_bersih}\n")

    return "Laporan berhasil dicatat ke dalam file dengan format yang rapi."

@tool
def kirim_dokumen_laporan(nomor_tujuan: str) -> str:
    """Kirim dokumen laporan magang (file .doc) ke nomor WhatsApp user.
    GUNAKAN ALAT INI KHUSUS saat user meminta mengirimkan/mengirim dokumen laporan magang,
    file laporan, atau catatan magang ke WhatsApp. Laporan dikirim sebagai FILE dokumen (bukan teks panjang),
    sehingga tidak terpotong. JANGAN gunakan alat ini untuk mengirim SOP.
    nomor_tujuan adalah nomor WhatsApp tujuan (bisa format 08xxx atau 62xxx)."""
    import base64

    isi_laporan = baca_laporan()
    if not isi_laporan or isi_laporan.startswith("(Belum ada"):
        return "Gagal mengirim: belum ada laporan magang yang tercatat di file."

    # Buat konten .doc (RTF) lalu encode ke base64
    doc_teks = buat_doc_dari_teks(isi_laporan)
    doc_bytes = doc_teks.encode("utf-8")
    doc_b64 = base64.b64encode(doc_bytes).decode("utf-8")
    media_data = f"data:application/msword;name=laporan_magang.doc;base64,{doc_b64}"

    # --- SISTEM KEAMANAN FORMAT NOMOR LENGKAP ---
    nomor_bersih = nomor_tujuan.strip().replace(" ", "").replace("-", "").replace("+", "")
    if nomor_bersih.startswith("0"):
        nomor_bersih = "62" + nomor_bersih[1:]
    elif nomor_bersih.startswith("8"):
        nomor_bersih = "62" + nomor_bersih

    token_wa = os.getenv("WA_TOKEN")
    url_api = "https://gate.whapi.cloud/messages/document"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {token_wa}"
    }
    payload = {
        "to": f"{nomor_bersih}@s.whatsapp.net",
        "media": media_data,
        "filename": "laporan_magang.doc",
        "caption": "Berikut dokumen laporan magang kamu."
    }

    try:
        print(f"\n[SISTEM] Mengirim FILE dokumen laporan ke {nomor_bersih}...")
        respons = requests.post(url_api, json=payload, headers=headers)
        print(f"[DEBUG WHAPI] Status: {respons.status_code} | {respons.text}")
        if respons.status_code == 200:
            return f"Dokumen laporan magang berhasil dikirim sebagai file ke {nomor_tujuan}."
        return f"Gagal mengirim dokumen: {respons.text}"
    except Exception as e:
        return f"Terjadi kesalahan koneksi: {str(e)}"

# ==========================================
# 🧠 INISIALISASI AGEN AI (SOP RAG System Prompt)
# ==========================================
daftar_tools = [kirim_whatsapp, kirim_email, tulis_laporan_ke_file, baca_laporan, kirim_dokumen_laporan]

# Daftar model Groq gratis sebagai fallback (selalu update jika ada yang decommissioned)
DAFTAR_MODEL = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama-3.2-3b-preview",
    "llama-3.2-1b-preview",
]

instruksi_sistem = f"""Kamu adalah ipzonex, assistent untuk membantu saif membuat laporan magang. 
Data Personal User:
- Nama User: Saif Ali Mushaddiq
- Institusi: Politeknik Negeri Indramayu
- Dosen Pembimbing: Fachrul Pralienka Bani Muhamad, M.Kom.
- Tempat Magang: Codepolitan

Kamu dibekali akses alat kirim_whatsapp, kirim_email, tulis_laporan_ke_file, baca_laporan, dan kirim_dokumen_laporan untuk membantu operasional serta mencatat, membaca, dan mengirim aktivitas harian.
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
- Saat memanggil alat 'tulis_laporan_ke_file', susun laporan dengan FORMAT RAPI seperti laporan resmi:
  * Gunakan heading berbentuk "1. Kegiatan", "2. Hasil", "3. Kendala", dll di awal baris.
  * Gunakan tanda "-" di awal untuk setiap poin/sub-poin.
  * Pisahkan tiap baris dengan karakter baris baru (enter) agar tersusun rapi, BUKAN semua dalam satu paragraf padat.
  * JANGAN gunakan tanda ** (bold markdown) di dalam isi laporan.
- Jangan memasukkan tanda kutip ganda berlebih yang bisa merusak format JSON.
- Jika laporan sangat panjang, tetap susun per poin, jangan dirangkum jadi satu kalimat.

ATURAN PENGIRIMAN DOKUMEN LAPORAN (SANGAT PENTING):
- Jika user meminta mengirimkan "dokumen magang", "file laporan", "laporan magang", atau "catatan magang" ke WhatsApp, KAMU WAJIB memanggil alat 'kirim_dokumen_laporan' (bukan kirim_whatsapp langsung, dan JANGAN mengirim isi SOP).
- Alat 'kirim_dokumen_laporan' sudah otomatis membaca isi file laporan_magang.txt dan mengirimkannya. Jangan mengisi pesan dengan isi SOP atau konteks perusahaan.
- Hanya gunakan alat 'kirim_whatsapp' untuk mengirim pesan obrolan biasa, bukan dokumen laporan.

FORMAT LAPORAN YANG RAPI:
- Jika user meminta "perbaiki format laporan", "rapikan laporan", atau "buat laporan seperti skripsi/laporan resmi", KAMU WAJIB memanggil 'baca_laporan' dulu, lalu panggil 'tulis_laporan_ke_file' dengan versi yang sudah ditata rapi: pakai heading bernomor (1. Kegiatan Harian, 2. Hasil Pembelajaran, 3. Kendala, 4. Rencana, 5. Refleksi), setiap poin mulai dengan "-", tanpa tanda **. Jangan biarkan laporan acak tanpa struktur."""

# Inisialisasi agen dengan fallback model: coba satu per satu sampai berhasil
agen_ai = None
for nama_model in DAFTAR_MODEL:
    try:
        model_ai = ChatGroq(model=nama_model, temperature=0.0)
        agen_ai = create_react_agent(model_ai, daftar_tools, prompt=instruksi_sistem)
        print(f"[INFO] Agen berhasil diinisialisasi dengan model: {nama_model}")
        break
    except Exception as e:
        print(f"[PERINGATAN] Gagal inisialisasi model {nama_model}: {e}. Mencoba model berikutnya...")
        continue

if agen_ai is None:
    raise RuntimeError("Semua model Groq gagal diinisialisasi. Periksa API key dan koneksi.")

# ==========================================
# 🛣️ ROUTE API UNTUK FRONTEND
# ==========================================
# Penyimpanan riwayat chat sederhana di memori (reset saat server restart)
riwayat_chat = []

class StrukturInput(BaseModel):
    pesan_user: str
    riwayat: list = []
@app.post("/chat")
async def handle_chat(data: StrukturInput):
    try:
        print(f"\n[FRONTEND] Menerima instruksi: '{data.pesan_user}'")

        # Bangun daftar pesan dari riwayat + pesan baru agar agen ingat konteks
        pesan_input = []
        for item in (data.riwayat or []):
            role = item.get("role")
            konten = item.get("content", "")
            if role == "user":
                pesan_input.append(("user", konten))
            elif role == "assistant":
                pesan_input.append(("assistant", konten))
        pesan_input.append(("user", data.pesan_user))

        # Jalankan Agen LangChain dengan fallback model saat runtime
        respons = None
        last_err = None
        for nama_model in DAFTAR_MODEL:
            try:
                model_coba = ChatGroq(model=nama_model, temperature=0.0)
                agen_coba = create_react_agent(model_coba, daftar_tools, prompt=instruksi_sistem)
                respons = agen_coba.invoke({"messages": pesan_input})
                break
            except Exception as e:
                last_err = e
                print(f"[PERINGATAN] Model {nama_model} gagal saat runtime: {e}. Mencoba berikutnya...")
                continue

        if respons is None:
            # Semua model gagal — beri tahu user dengan ramah, jangan crash
            return {"jawaban": "Maaf, semua model AI sedang tidak tersedia atau mengalami gangguan. Silakan coba beberapa saat lagi. (Detail: " + str(last_err)[:200] + ")"}
        
        # Ambil daftar pesan dari respons agen
        daftar_pesan = respons.get("messages", [])
        
        if len(daftar_pesan) > 0:
            # Ambil pesan AI terakhir (bukan ToolMessage) agar balasan terasa natural
            balasan_akhir = ""
            for pesan in reversed(daftar_pesan):
                if type(pesan).__name__ == "AIMessage" and pesan.content:
                    balasan_akhir = pesan.content
                    break
            # Fallback ke pesan terakhakir apa pun
            if not balasan_akhir:
                balasan_akhir = daftar_pesan[-1].content
            
            # Pengaman tambahan: Jika AI memberikan jawaban kosong setelah panggil tool
            if not balasan_akhir:
                balasan_akhir = "Tugas berhasil dilaksanakan melalui sistem internal."
        else:
            balasan_akhir = "Maaf, sistem gagal memproses teks jawaban."

        # Simpan ke riwayat (user + assistant) untuk konteks berikutnya
        riwayat_chat.append({"role": "user", "content": data.pesan_user})
        riwayat_chat.append({"role": "assistant", "content": balasan_akhir})
            
        return {"jawaban": balasan_akhir, "riwayat": riwayat_chat}
        
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

# ==========================================
# 🌐 ROUTE UI - Serve frontend HTML langsung dari backend
# ==========================================
@app.get("/")
def tampilkan_ui():
    return FileResponse("index.html")

@app.post("/reset-chat")
def reset_chat():
    riwayat_chat.clear()
    return {"status": "ok"}

# ==========================================
# 📄 DOWNLOAD DOKUMEN LAPORAN (.doc)
# ==========================================
def escape_rtf(teks: str) -> str:
    return teks.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")

def buat_doc_dari_teks(teks: str) -> str:
    """Mengubah teks laporan menjadi format .doc (RTF) yang rapi dan terstruktur."""
    baris = teks.split("\n")
    hasil = []
    for b in baris:
        b = b.rstrip()
        if not b.strip():
            continue
        # Hapus tanda markdown berlebih agar tampil rapi
        baris_bersih = b.replace("**", "").replace("â†’", "->").strip()

        # Judul dokumen (baris berisi tanggal [....] di awal dianggap header harian)
        if baris_bersih.startswith("[") and "]" in baris_bersih:
            isi = escape_rtf(baris_bersih)
            hasil.append(f"\\par\\pard\\qc\\b\\fs26 {isi}\\b0\\par")
            hasil.append("\\pard\\qc\\fs20 Laporan Kegiatan Magang Harian\\par\\par")
            continue

        # Heading (dimulai dengan angka diikuti titik, misal "1. ...")
        if any(baris_bersih.startswith(f"{i}.") for i in range(1, 10)) and len(baris_bersih) < 80:
            isi = escape_rtf(baris_bersih)
            hasil.append(f"\\par\\pard\\b\\fs24 {isi}\\b0\\par")
            continue

        # Poin (dimulai dengan - atau *)
        if baris_bersih.startswith("-") or baris_bersih.startswith("*"):
            isi = escape_rtf(baris_bersih.lstrip("-* ").strip())
            hasil.append(f"\\pard\\li360\\bullet\\fs22 {isi}\\par")
            continue

        # Paragraf biasa
        isi = escape_rtf(baris_bersih)
        hasil.append(f"\\pard\\fs22 {isi}\\par")

    body = "\n".join(hasil)
    return (
        "{\\rtf1\\ansi\\ansicpg1252\\deff0\\deflang1057\n"
        "{\\fonttbl{\\f0\\fnil\\fcharset0 Calibri;}}\n"
        "\\viewkind4\\uc1\\pard\\f0\n"
        f"{body}\n"
        "}"
    )

@app.get("/download-laporan")
def download_laporan():
    try:
        with open("laporan_magang.txt", "r", encoding="utf-8") as f:
            isi = f.read().strip()
    except FileNotFoundError:
        isi = "(Belum ada laporan magang yang dicatat)"

    if not isi:
        isi = "(Belum ada laporan magang yang dicatat)"

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nama_file = f"laporan_magang_{timestamp}.doc"
    doc_content = buat_doc_dari_teks(isi).encode("utf-8")

    from fastapi.responses import Response
    return Response(
        content=doc_content,
        media_type="application/msword",
        headers={"Content-Disposition": f'attachment; filename="{nama_file}"'}
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
