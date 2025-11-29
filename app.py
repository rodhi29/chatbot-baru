import streamlit as st
import os
from google import genai
from google.genai import types

# --- 1. Konfigurasi Halaman Web Streamlit ---
st.set_page_config(
    page_title="Teman Bicara Cerdas (TBC)", 
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("💬 Teman Bicara Cerdas (TBC)")
st.caption("Didukung oleh Google Gemini 2.5 Flash")

# --- 2. Inisialisasi Klien Gemini & Konfigurasi Sistem ---

# Tentukan System Instruction untuk kepribadian yang manusiawi
SYSTEM_INSTRUCTION_PROMPT = (
    "Anda adalah 'Teman Bicara Cerdas' (TBC). Anda adalah asisten AI yang ramah, santai, "
    "dan suportif. Selalu gunakan bahasa sehari-hari yang sopan (misalnya: 'Halo!', 'Tentu saja!', "
    "'Gimana kabarnya?'). Jangan pernah memberikan jawaban yang terlalu kaku atau formal seperti kamus. "
    "Gunakan emoji yang relevan untuk menambahkan kesan bersahabat dan personal. "
    "Tanggapi pertanyaan dengan cepat, tapi jangan ragu mengakui jika Anda tidak tahu sesuatu."
)

if "client" not in st.session_state:
    try:
        # Mencoba membuat klien. Kunci API diambil dari environment variable (Secrets)
        st.session_state.client = genai.Client()
    except Exception as e:
        st.error("⚠️ Kesalahan Inisialisasi: Kunci API Gemini (GOOGLE_API_KEY) tidak ditemukan di Secrets.")
        st.warning("Silakan periksa pengaturan 'Secrets' di Streamlit Cloud Anda.")
        st.stop()

# --- 3. Inisialisasi Riwayat Pesan Lokal ---
# Riwayat akan disimpan dalam list Python untuk memudahkan manipulasi Edit/Hapus
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. Fungsi-Fungsi Manipulasi Chat (Edit & Hapus) ---

def rebuild_chat_session():
    """Membangun kembali sesi chat Gemini dengan riwayat pesan yang tersisa."""
    
    # Objek konfigurasi dengan System Instruction
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION_PROMPT
    )
    
    # Buat sesi baru
    new_chat = st.session_state.client.chats.create(
        model="gemini-2.5-flash", 
        config=config
    )
    
    # Isi sesi baru dengan riwayat pesan yang tersisa di st.session_state.messages
    contents = []
    for msg in st.session_state.messages:
        # Hanya masukkan pesan 'user' ke dalam riwayat baru, model akan merespon ulang secara berurutan
        if msg["role"] == "user":
            contents.append(
                types.Content(
                    role="user", 
                    # SOLUSI TYPEERROR: Gunakan inisialisasi eksplisit untuk Part
                    parts=[types.Part(text=msg["text"])] 
                )
            )
        # Jika itu pesan 'assistant', masukkan juga agar riwayat kronologis tetap utuh
        elif msg["role"] == "assistant":
            contents.append(
                types.Content(
                    role="model", 
                    parts=[types.Part(text=msg["text"])]
                )
            )

    # Menggunakan metode private untuk sinkronisasi riwayat
    # Ini penting agar model tahu konteksnya tanpa harus memanggil send_message() untuk setiap pesan lama
    new_chat._history = contents
    
    st.session_state.chat_session = new_chat
    
    # Menghentikan skrip untuk memaksa render ulang antarmuka
    st.rerun() 

# Panggil rebuild_chat_session() pertama kali saat aplikasi dimulai
if "chat_session" not in st.session_state:
    rebuild_chat_session()


def delete_message(index):
    """Menghapus pesan pengguna dan respon model yang terkait."""
    
    # Hapus pesan pengguna pada index
    st.session_state.messages.pop(index)
    
    # Hapus pesan balasan dari model yang terkait (asumsi balasan adalah index berikutnya)
    if index < len(st.session_state.messages) and st.session_state.messages[index]["role"] == "assistant":
         st.session_state.messages.pop(index)
         
    # Bangun ulang sesi chat Gemini
    rebuild_chat_session()
        
def edit_message(index, new_text):
    """Mengedit pesan pengguna dan meminta model merespons ulang."""
    
    # Perbarui teks pesan pengguna
    st.session_state.messages[index]["text"] = new_text
    
    # Hapus balasan model lama (jika ada)
    if index + 1 < len(st.session_state.messages) and st.session_state.messages[index + 1]["role"] == "assistant":
        st.session_state.messages.pop(index + 1)
        
    # Bangun ulang sesi chat Gemini setelah pengeditan
    rebuild_chat_session()


# --- 5. Menampilkan Riwayat Pesan dan Tombol Edit/Hapus ---

# Kita iterasi melalui pesan lokal yang sudah kita simpan
for i, msg in enumerate(st.session_state.messages):
    
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

# --- 6. Form Edit Pesan (Hanya ditampilkan jika mode edit aktif) ---
if "editing_index" in st.session_state and st.session_state.editing_index >= 0:
    edit_index = st.session_state.editing_index
    current_text = st.session_state.messages[edit_index]["text"]
    
    st.subheader(f"✏️ Edit Pesan ke-{edit_index + 1}")
    
    with st.form(key=f"edit_form_{edit_index}"):
        # Text area dengan nilai pesan saat ini
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

# --- 7. Penanganan Input Chat Baru ---
if prompt := st.chat_input("Tanyakan sesuatu..."):
    
    # Tambahkan prompt pengguna ke riwayat lokal
    st.session_state.messages.append({"role": "user", "text": prompt})
    
    # Tampilkan prompt pengguna segera
    with st.chat_message("user"):
        st.markdown(prompt)

    # Kirim prompt ke Gemini dan tampilkan respons
    try:
        with st.spinner("🤖 TBC sedang merenung..."):
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
        st.error(f"Terjadi kesalahan saat mengirim pesan ke Gemini: {e}")
        # Hapus pesan pengguna terakhir jika terjadi error
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            st.session_state.messages.pop() 


# --- 8. Informasi Samping (Sidebar Opsional) ---
with st.sidebar:
    st.subheader("Petunjuk Interaksi")
    st.info(
        "TBC memiliki kepribadian yang ramah dan santai. "
        "Tombol ❌ akan menghapus pesan Anda dan balasan bot, lalu memulai ulang percakapan."
        "\n\nTombol ✏️ akan memunculkan kotak edit. Setelah disimpan, TBC akan merespons pesan yang diedit."
    )
    st.markdown("---")
    st.markdown("Model: **`gemini-2.5-flash`**")

# --- Akhir app.py ---