import streamlit as st
import os
from google import genai
from google.genai import types
import base64 # Untuk mengelola gambar

# --- 1. Konfigurasi Halaman Web Streamlit ---
st.set_page_config(
    page_title="Teman Bicara Cerdas (TBC)", 
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("💬 Teman Bicara Cerdas (TBC)")
st.caption("Didukung oleh Google Gemini 2.5 Flash (Multimodal)")

# --- 2. Inisialisasi Klien Gemini & Konfigurasi Sistem ---

SYSTEM_INSTRUCTION_PROMPT = (
    "Anda adalah 'Teman Bicara Cerdas' (TBC). Anda adalah asisten AI yang ramah, santai, "
    "dan suportif. Selalu gunakan bahasa sehari-hari yang sopan (misalnya: 'Halo!', 'Tentu saja!', "
    "'Gimana kabarnya?'). Jangan pernah memberikan jawaban yang terlalu kaku atau formal seperti kamus. "
    "Gunakan emoji yang relevan untuk menambahkan kesan bersahabat dan personal. "
    "Tanggapi pertanyaan dengan cepat, tapi jangan ragu mengakui jika Anda tidak tahu sesuatu."
    "Jika ada gambar yang diunggah, coba analisis gambar tersebut dan berikan tanggapan yang relevan."
)

if "client" not in st.session_state:
    try:
        st.session_state.client = genai.Client()
    except Exception as e:
        st.error("⚠️ Kesalahan Inisialisasi: Kunci API Gemini (GOOGLE_API_KEY) tidak ditemukan di Secrets.")
        st.warning("Silakan periksa pengaturan 'Secrets' di Streamlit Cloud Anda.")
        st.stop()

# --- 3. Inisialisasi Riwayat Pesan Lokal ---
# Riwayat akan menyimpan {'role': ..., 'text': ..., 'image_data': ...}
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Fungsi Helper untuk Gambar ---
def get_image_as_base64(uploaded_file):
    """Mengubah uploaded_file Streamlit menjadi string base64."""
    if uploaded_file is not None:
        return base64.b64encode(uploaded_file.read()).decode('utf-8')
    return None

def display_image_from_base64(base64_string, caption=""):
    """Menampilkan gambar dari string base64."""
    if base64_string:
        st.image(f"data:image/jpeg;base64,{base64_string}", caption=caption, use_column_width=True)

# --- 4. Fungsi-Fungsi Manipulasi Chat (Edit & Hapus) ---

def rebuild_chat_session():
    """Membangun kembali sesi chat Gemini dengan riwayat pesan yang tersisa."""
    
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION_PROMPT
    )
    
    if "chat_session" in st.session_state:
        del st.session_state.chat_session
        
    new_chat = st.session_state.client.chats.create(
        model="gemini-2.5-flash", # Pastikan model ini mendukung multimodal
        config=config
    )
    
    contents = []
    for msg in st.session_state.messages:
        parts = []
        if msg["text"]:
            parts.append(types.Part(text=msg["text"]))
        if msg["image_data"]:
            # Jika ada data gambar, tambahkan sebagai part gambar
            parts.append(types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=base64.b64decode(msg["image_data"]))))

        if parts: # Pastikan ada konten sebelum append
            if msg["role"] == "user":
                contents.append(types.Content(role="user", parts=parts))
            elif msg["role"] == "assistant":
                contents.append(types.Content(role="model", parts=parts))

    new_chat._history = contents
    
    st.session_state.chat_session = new_chat
    st.rerun() 


if "chat_session" not in st.session_state:
    rebuild_chat_session()


def delete_message(index):
    """Menghapus pesan pengguna dan respon model yang terkait."""
    st.session_state.messages.pop(index)
    if index < len(st.session_state.messages) and st.session_state.messages[index]["role"] == "assistant":
         st.session_state.messages.pop(index)
    rebuild_chat_session()
        
def edit_message(index, new_text):
    """Mengedit pesan pengguna dan menandai untuk pengiriman ulang."""
    st.session_state.messages[index]["text"] = new_text
    # Gambar tidak diedit, hanya teks
    
    if index + 1 < len(st.session_state.messages) and st.session_state.messages[index + 1]["role"] == "assistant":
        st.session_state.messages.pop(index + 1)
        
    st.session_state.resend_last_message = True 
    rebuild_chat_session()


# --- 5. Menampilkan Riwayat Pesan dan Tombol Edit/Hapus ---

for i, msg in enumerate(st.session_state.messages):
    
    chat_container = st.container()

    with chat_container:
        role_display = "user" if msg["role"] == "user" else "assistant"
        
        with st.chat_message(role_display):
            # Tampilkan gambar jika ada
            if msg["image_data"]:
                display_image_from_base64(msg["image_data"], caption=f"Gambar dari {role_display}")
            
            # Tampilkan teks
            if msg["text"]:
                # Jika itu pesan pengguna, tampilkan tombol Edit dan Hapus
                if msg["role"] == "user":
                    col1, col2, col3 = st.columns([10, 1, 1])
                    with col1:
                        st.markdown(msg["text"])
                    with col2:
                        st.button("❌", key=f"del_{i}", help="Hapus pesan ini", on_click=delete_message, args=(i,))
                    with col3:
                        # Tombol Edit hanya untuk teks, gambar tidak bisa diedit via form ini
                        if st.button("✏️", key=f"edit_btn_{i}", help="Edit pesan ini"):
                            st.session_state.editing_index = i
                            st.rerun() 
                else:
                    # Pesan dari bot
                    st.markdown(msg["text"])
            else:
                # Jika tidak ada teks tapi ada gambar, tambahkan teks default agar tidak kosong
                if msg["image_data"] and msg["role"] == "user":
                    st.markdown("*Mengirim gambar tanpa teks*")


# --- 6. Form Edit Pesan (Hanya ditampilkan jika mode edit aktif) ---
if "editing_index" in st.session_state and st.session_state.editing_index >= 0:
    edit_index = st.session_state.editing_index
    current_text = st.session_state.messages[edit_index]["text"]
    
    st.subheader(f"✏️ Edit Pesan ke-{edit_index + 1}")
    
    with st.form(key=f"edit_form_{edit_index}"):
        new_text = st.text_area("Teks Baru:", value=current_text, key="edit_text_area")
        # Jika ada gambar di pesan yang diedit, tampilkan sebagai referensi
        if st.session_state.messages[edit_index]["image_data"]:
            display_image_from_base64(st.session_state.messages[edit_index]["image_data"], caption="Gambar asli pesan ini:")

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

# --- 7. Penanganan Input Chat Baru & Gambar ---
col_text_input, col_image_uploader = st.columns([3, 1])

with col_text_input:
    prompt = st.chat_input("Tanyakan sesuatu...", key="main_chat_input")

with col_image_uploader:
    uploaded_image = st.file_uploader("Upload Gambar", type=["jpg", "jpeg", "png"], key="image_uploader")

if prompt or uploaded_image:
    
    user_message_text = prompt if prompt else ""
    user_image_data_base64 = get_image_as_base64(uploaded_image)
    
    # Tambahkan prompt pengguna dan/atau gambar ke riwayat lokal
    st.session_state.messages.append({
        "role": "user", 
        "text": user_message_text, 
        "image_data": user_image_data_base64
    })
    
    # Tampilkan prompt pengguna segera
    with st.chat_message("user"):
        if user_image_data_base64:
            display_image_from_base64(user_image_data_base64, caption="Gambar Anda")
        if user_message_text:
            st.markdown(user_message_text)
        elif not user_message_text and user_image_data_base64:
            st.markdown("*Mengirim gambar tanpa teks*")


    # Siapkan konten untuk dikirim ke Gemini
    parts_to_send = []
    if user_message_text:
        parts_to_send.append(types.Part(text=user_message_text))
    if user_image_data_base64:
        parts_to_send.append(types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=base64.b64decode(user_image_data_base64))))
    
    # Hanya kirim jika ada teks atau gambar
    if parts_to_send:
        try:
            with st.spinner("🤖 TBC sedang menganalisis..."):
                response = st.session_state.chat_session.send_message(parts_to_send)
                response_text = response.parts[0].text # Gemini biasanya merespons dengan teks
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "text": response_text, 
                    "image_data": None # Asumsi Gemini hanya merespons teks
                })
                
                with st.chat_message("assistant"):
                    st.markdown(response_text)
                    
        except Exception as e:
            st.error(f"Terjadi kesalahan saat mengirim pesan ke Gemini: {e}")
            if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                st.session_state.messages.pop() 
    else:
        # Jika tidak ada prompt dan tidak ada gambar yang diunggah
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            st.session_state.messages.pop()
        st.warning("Mohon masukkan teks atau unggah gambar.")

# --- 8. Blok Pengiriman Ulang Otomatis Setelah Edit (SOLUSI RESPONS) ---
if "resend_last_message" in st.session_state and st.session_state.resend_last_message:
    
    st.session_state.resend_last_message = False 
    
    # Pesan terakhir di riwayat lokal adalah pesan yang baru saja diedit/dikoreksi
    last_user_msg = st.session_state.messages[-1]
    
    parts_to_resend = []
    if last_user_msg["text"]:
        parts_to_resend.append(types.Part(text=last_user_msg["text"]))
    if last_user_msg["image_data"]:
        parts_to_resend.append(types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=base64.b64decode(last_user_msg["image_data"]))))
    
    try:
        with st.spinner("🤖 TBC sedang memproses ulang pesan yang diedit..."):
            response = st.session_state.chat_session.send_message(parts_to_resend)
            response_text = response.parts[0].text
            
            st.session_state.messages.append({
                "role": "assistant", 
                "text": response_text, 
                "image_data": None # Asumsi Gemini hanya merespons teks
            })
            
            with st.chat_message("assistant"):
                st.markdown(response_text)
                
    except Exception as e:
        st.error(f"Terjadi kesalahan saat mengirim pesan yang diedit ke Gemini: {e}")
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            st.session_state.messages.pop()
    
    st.rerun()

# --- 9. Informasi Samping (Sidebar Opsional) ---
with st.sidebar:
    st.subheader("Petunjuk Interaksi")
    st.info(
        "TBC memiliki kepribadian yang ramah dan santai. "
        "Tombol ❌ akan menghapus pesan Anda dan balasan bot."
        "\n\nTombol ✏️ akan memunculkan kotak edit (hanya teks) dan TBC akan **otomatis** merespons pesan yang diedit."
        "\n\nAnda sekarang bisa **mengunggah gambar**! TBC akan mencoba menganalisisnya."
    )
    st.markdown("---")
    st.markdown("Model: **`gemini-2.5-flash` (Multimodal)**")