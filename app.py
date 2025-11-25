import streamlit as st
import os
from google import genai

# --- 1. Konfigurasi Halaman Web Streamlit ---
st.set_page_config(
    page_title="Gemini Chatbot Online", 
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("💬 Chatbot Pintar Bertenaga Gemini")
st.caption("Dibuat menggunakan Streamlit dan Google Gemini API")

# --- 2. Inisialisasi Klien Gemini (Hanya Sekali per Sesi) ---
# Memastikan Klien API (Koneksi) hanya dibuat sekali per sesi.
# Kunci API dibaca dari environment variable GOOGLE_API_KEY
if "client" not in st.session_state:
    try:
        # Mencoba membuat klien. Kunci API diambil dari environment variable (Secrets di Streamlit Cloud)
        st.session_state.client = genai.Client()
    except Exception as e:
        # Menangani kegagalan jika Kunci API tidak ditemukan atau tidak valid
        st.error("⚠️ Kesalahan Inisialisasi: Kunci API Gemini (GOOGLE_API_KEY) tidak ditemukan di Secrets.")
        st.warning("Silakan periksa pengaturan 'Secrets' di Streamlit Cloud Anda.")
        st.stop() # Hentikan aplikasi jika API key tidak ada.

# --- 3. Inisialisasi Sesi Chat (Hanya Sekali per Sesi) ---
# Memastikan Sesi Chat dibuat hanya sekali per sesi pengguna.
if "chat_session" not in st.session_state:
    # Menggunakan model gemini-2.5-flash untuk performa cepat
    st.session_state.chat_session = st.session_state.client.chats.create(
        model="gemini-2.5-flash"
    )

# --- 4. Fungsi Utama: Menampilkan dan Memproses Chat ---

# Menampilkan riwayat pesan yang sudah ada
for message in st.session_state.chat_session.get_history():
    # Menentukan peran untuk tampilan (user atau assistant)
    role_display = "user" if message.role == "user" else "assistant"
    
    # KOREKSI PENTING: Mengakses teks dari 'parts' objek Content
    # Ini memperbaiki AttributeError yang terjadi sebelumnya
    if message.parts and message.parts[0].text:
        text_content = message.parts[0].text
        with st.chat_message(role_display):
            st.markdown(text_content)

# Input pengguna baru
if prompt := st.chat_input("Tanyakan sesuatu..."):
    # Tampilkan prompt pengguna segera
    with st.chat_message("user"):
        st.markdown(prompt)

    # Kirim prompt ke Gemini dan tampilkan respons
    try:
        with st.spinner("🤖 Bot sedang berpikir..."):
            # Mengirim pesan ke sesi chat yang sudah disimpan
            response = st.session_state.chat_session.send_message(prompt)
            
            # Tampilkan respons dari model
            # Respons dari send_message() adalah objek Message yang juga perlu diakses melalui parts[0].text
            response_text = response.parts[0].text
            with st.chat_message("assistant"):
                st.markdown(response_text)
                
    except Exception as e:
        # Menangani kesalahan jika API gagal mengirim/menerima
        st.error(f"Terjadi kesalahan saat mengirim pesan ke Gemini: {e}")


# --- 5. Informasi Samping (Sidebar Opsional) ---
with st.sidebar:
    st.subheader("Petunjuk Deployment")
    st.info(
        "Pastikan Anda telah mengatur 'Secrets' di Streamlit Cloud dengan kunci: "
        "\n\n**`GOOGLE_API_KEY`**"
    )
    st.markdown("---")
    st.markdown("Model yang digunakan: **`gemini-2.5-flash`** (Cepat & Hemat)")

# --- Akhir app.py ---