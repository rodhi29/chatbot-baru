import streamlit as st
import os
from google import genai
from google.genai import types

# --- 1. Konfigurasi Halaman Web Streamlit ---
st.set_page_config(
    page_title="Gemini Chatbot Interaktif", 
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("💬 Chatbot Interaktif dengan Edit & Hapus")

# --- 2. Inisialisasi Klien Gemini (Hanya Sekali per Sesi) ---
if "client" not in st.session_state:
    try:
        st.session_state.client = genai.Client()
    except Exception as e:
        st.error("⚠️ Kesalahan Inisialisasi: Kunci API Gemini (GOOGLE_API_KEY) tidak ditemukan.")
        st.warning("Silakan periksa pengaturan 'Secrets' di Streamlit Cloud Anda.")
        st.stop()

# --- 3. Inisialisasi Riwayat Pesan Lokal ---
# Riwayat akan disimpan dalam list Python untuk memudahkan manipulasi
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. Fungsi-Fungsi Baru untuk Manipulasi Chat ---

### FITUR BARU: HAPUS & EDIT ###

def rebuild_chat_session():
    """Membangun kembali sesi chat Gemini dengan riwayat pesan yang tersisa."""
    # Hapus sesi lama
    del st.session_state.chat_session
    
    # Buat sesi baru
    new_chat = st.session_state.client.chats.create(model="gemini-2.5-flash")
    
    # Isi sesi baru dengan riwayat pesan yang tersisa di st.session_state.messages
    contents = []
    for msg in st.session_state.messages:
        # Pastikan hanya pesan 'user' yang dimasukkan kembali, karena Gemini akan merespon ulang
        if msg["role"] == "user":
            contents.append(
                types.Content(
                    role="user", 
                    parts=[types.Part.from_text(msg["text"])]
                )
            )
            
    # Kirim semua riwayat sebagai satu batch (kecuali pesan terakhir, yang akan dikirim terpisah)
    if contents:
        new_chat.send_message(contents)
        
    st.session_state.chat_session = new_chat
    
    # Menghentikan skrip untuk memaksa render ulang antarmuka
    st.rerun() 

def delete_message(index):
    """Menghapus pesan pengguna dan respon model yang terkait."""
    
    # Hapus pesan pengguna (index) dan pesan model setelahnya (index + 1)
    if index < len(st.session_state.messages):
        # Hapus pesan pengguna
        st.session_state.messages.pop(index)
        
        # Hapus pesan balasan dari model yang terkait (jika ada dan merupakan balasan)
        if index < len(st.session_state.messages) and st.session_state.messages[index]["role"] == "assistant":
             st.session_state.messages.pop(index)
             
        # Bangun ulang sesi chat Gemini setelah penghapusan
        rebuild_chat_session()
        
def edit_message(index, new_text):
    """Mengedit pesan pengguna, lalu membangun kembali sesi chat."""
    
    # Perbarui teks pesan pengguna
    st.session_state.messages[index]["text"] = new_text
    
    # Hapus balasan model lama (jika ada)
    if index + 1 < len(st.session_state.messages) and st.session_state.messages[index + 1]["role"] == "assistant":
        st.session_state.messages.pop(index + 1)
        
    # Bangun ulang sesi chat Gemini setelah pengeditan
    rebuild_chat_session()
    
### --- END FITUR BARU --- ###

# --- 5. Inisialisasi Sesi Chat Gemini (Jika belum ada) ---
if "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.client.chats.create(
        model="gemini-2.5-flash"
    )

# --- 6. Menampilkan Riwayat Pesan dan Tombol Edit/Hapus ---

# Kita iterasi melalui pesan lokal yang sudah kita simpan
for i, msg in enumerate(st.session_state.messages):
    
    # Gunakan container untuk menempatkan tombol di samping pesan
    chat_container = st.container()

    with chat_container:
        role_display = "user" if msg["role"] == "user" else "assistant"
        
        with st.chat_message(role_display):
            
            # Jika itu pesan pengguna, tampilkan tombol Edit dan Hapus
            if msg["role"] == "user":
                
                # Gunakan kolom untuk menempatkan tombol di sebelah pesan
                col1, col2, col3 = st.columns([10, 1, 1])
                
                with col1:
                    # Tampilkan teks
                    st.markdown(msg["text"])
                    
                with col2:
                    # Tombol Hapus
                    st.button("❌", key=f"del_{i}", help="Hapus pesan ini", on_click=delete_message, args=(i,))

                with col3:
                    # Tombol Edit (menggunakan toggle untuk menampilkan input teks)
                    if st.button("✏️", key=f"edit_btn_{i}", help="Edit pesan ini"):
                        # Set status edit ke index saat ini
                        st.session_state.editing_index = i
                        st.rerun() # Rerun untuk menampilkan form edit
                        
            else:
                # Pesan dari bot, tidak perlu tombol edit/hapus
                st.markdown(msg["text"])

# --- 7. Form Edit Pesan (Hanya ditampilkan jika mode edit aktif) ---
if "editing_index" in st.session_state:
    edit_index = st.session_state.editing_index
    current_text = st.session_state.messages[edit_index]["text"]
    
    st.subheader(f"Edit Pesan ke-{edit_index + 1}")
    
    with st.form(key=f"edit_form_{edit_index}"):
        new_text = st.text_area("Teks Baru:", value=current_text, key="edit_text_area")
        
        col_ok, col_cancel = st.columns([1, 10])
        
        with col_ok:
            if st.form_submit_button("Simpan", type="primary"):
                edit_message(edit_index, new_text)
                del st.session_state.editing_index
                st.rerun()
                
        with col_cancel:
            if st.form_submit_button("Batal"):
                del st.session_state.editing_index
                st.rerun()

# --- 8. Penanganan Input Chat Baru ---
if prompt := st.chat_input("Tanyakan sesuatu..."):
    
    # Tambahkan prompt pengguna ke riwayat lokal
    st.session_state.messages.append({"role": "user", "text": prompt})
    
    # Tampilkan prompt pengguna segera
    with st.chat_message("user"):
        st.markdown(prompt)

    # Kirim prompt ke Gemini dan tampilkan respons
    try:
        with st.spinner("🤖 Bot sedang berpikir..."):
            # Mengirim pesan ke sesi chat yang sudah disimpan
            response = st.session_state.chat_session.send_message(prompt)
            
            # Ambil teks respons
            response_text = response.parts[0].text
            
            # Tambahkan respons model ke riwayat lokal
            st.session_state.messages.append({"role": "assistant", "text": response_text})
            
            # Tampilkan respons dari model
            with st.chat_message("assistant"):
                st.markdown(response_text)
                
    except Exception as e:
        # Menangani kesalahan jika API gagal mengirim/menerima
        st.error(f"Terjadi kesalahan saat mengirim pesan ke Gemini: {e}")
        # Hapus pesan pengguna terakhir jika terjadi error
        st.session_state.messages.pop() 


# --- 9. Informasi Samping (Sidebar Opsional) ---
with st.sidebar:
    st.subheader("Petunjuk Interaksi")
    st.info(
        "Tombol ❌ akan menghapus pesan Anda dan balasan bot, lalu memulai ulang percakapan dari pesan sebelumnya."
        "\n\nTombol ✏️ akan memunculkan kotak edit. Setelah disimpan, bot akan merespons pesan yang diedit."
    )
    st.markdown("---")
    st.markdown("Model: **`gemini-2.5-flash`**")

# --- Akhir app.py ---