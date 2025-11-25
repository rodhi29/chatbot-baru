import streamlit as st
import os
from google import genai

# Konfigurasi Halaman Web
st.set_page_config(page_title="Gemini Chatbot Online", layout="wide")
st.title("chatbot online")

# Dapatkan Kunci API dari variabel lingkungan (ini penting untuk deployment)
# Anda perlu mengatur variabel lingkungan GOOGLE_API_KEY
try:
    client = genai.Client()
except Exception:
    st.error("Kunci API Gemini tidak ditemukan. Harap atur GOOGLE_API_KEY.")
    st.stop()


# Inisialisasi sesi chat
if "chat_session" not in st.session_state:
    st.session_state.chat_session = client.chats.create(model="gemini-2.5-flash")

# Tampilkan riwayat pesan
for message in st.session_state.chat_session.get_history():
    # Asumsi role 'user' adalah pengguna, dan 'model' adalah bot
    role = "user" if message.role == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(message.text)

# Input pengguna baru
if prompt := st.chat_input("Tanyakan sesuatu..."):
    # Tampilkan pesan pengguna di antarmuka
    with st.chat_message("user"):
        st.markdown(prompt)

    # Kirim prompt ke Gemini dan tampilkan respons
    with st.spinner("Bot sedang berpikir..."):
        try:
            response = st.session_state.chat_session.send_message(prompt)
            with st.chat_message("assistant"):
                st.markdown(response.text)
        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")