import streamlit as st
import os
from google import genai
from google.genai import types
import base64
import openai # Pustaka OpenAI untuk generate gambar
from streamlit.components.v1 import html # PENTING: Untuk memasukkan JS STT

# --- 1. Konfigurasi Halaman Web Streamlit ---
st.set_page_config(
    page_title="Teman Bicara Cerdas (TBC)", 
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("💬 Teman Bicara Cerdas (TBC)")
st.caption("Didukung oleh Google Gemini 2.5 Flash & OpenAI DALL-E 🖼️")

# --- 2. Inisialisasi Klien Gemini & OpenAI ---

SYSTEM_INSTRUCTION_PROMPT = (
    "Anda adalah 'Teman Bicara Cerdas' (TBC). Anda adalah asisten AI yang ramah, santai, "
    "dan suportif. Selalu gunakan bahasa sehari-hari yang sopan (misalnya: 'Halo!', 'Tentu saja!', "
    "'Gimana kabarnya?'). Jangan pernah memberikan jawaban yang terlalu kaku atau formal seperti kamus. "
    "Gunakan emoji yang relevan untuk menambahkan kesan bersahabat dan personal. "
    "Tanggapi pertanyaan dengan cepat, tapi jangan ragu mengakui jika Anda tidak tahu sesuatu."
    "Jika ada gambar yang diunggah, coba analisis gambar tersebut dan berikan tanggapan yang relevan."
    "Jika pengguna meminta Anda untuk membuat atau menggambar sesuatu, contoh: 'buatkan gambar kucing', 'visualisasikan pemandangan', "
    "maka Anda harus MENCIPTAKAN GAMBAR. Jangan jawab dengan teks saja. "
    "Jika Anda berhasil membuat gambar, berikan respons teks singkat seperti 'Ini dia gambarnya! 🖼️' atau 'Sudah saya buatkan: 🎨'"
)

# Inisialisasi Gemini Client
if "gemini_client" not in st.session_state:
    try:
        # st.secrets["GOOGLE_API_KEY"] diasumsikan sudah ada di secrets
        st.session_state.gemini_client = genai.Client()
    except Exception as e:
        st.error("⚠️ Kesalahan Inisialisasi Gemini: Kunci API Gemini (GOOGLE_API_KEY) tidak ditemukan di Secrets.")
        st.warning("Silakan periksa pengaturan 'Secrets' Anda.")
        st.stop()

# Inisialisasi OpenAI Client (Diperlukan untuk Generate Gambar)
if "openai_client" not in st.session_state:
    try:
        st.session_state.openai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    except Exception as e:
        st.error("⚠️ Kesalahan Inisialisasi OpenAI: Kunci API OpenAI (OPENAI_API_KEY) tidak ditemukan di Secrets.")
        st.warning("Silakan periksa pengaturan 'Secrets' Anda.")
        # Lanjutkan tanpa OpenAI jika gagal, tetapi fitur generate gambar tidak akan berfungsi
        pass 

# --- 3. Inisialisasi Riwayat Pesan Lokal ---
# Riwayat akan menyimpan {'role': ..., 'text': ..., 'image_data': ..., 'generated_image_url': ...}
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Fungsi Helper untuk Gambar Upload ---
def get_image_as_base64(uploaded_file):
    """Mengubah uploaded_file Streamlit menjadi string base64."""
    if uploaded_file is not None:
        # Mengatur ulang file pointer ke awal sebelum membaca
        uploaded_file.seek(0)
        return base64.b64encode(uploaded_file.read()).decode('utf-8')
    return None

def display_image_from_base64(base64_string, caption=""):
    """Menampilkan gambar dari string base64."""
    if base64_string:
        st.image(f"data:image/jpeg;base64,{base64_string}", caption=caption, use_column_width=True)

# --- Fungsi Helper untuk Generate Gambar ---
def generate_image_with_dalle(prompt_text):
    """Memanggil DALL-E API untuk membuat gambar."""
    if "openai_client" not in st.session_state:
        st.error("OpenAI Client belum terinisialisasi. Fitur Generate Gambar non-aktif.")
        return None
    try:
        response = st.session_state.openai_client.images.generate(
            model="dall-e-3", 
            prompt=prompt_text,
            size="1024x1024", 
            quality="standard", 
            n=1, 
        )
        image_url = response.data[0].url
        return image_url
    except Exception as e:
        st.error(f"Gagal membuat gambar dengan DALL-E: {e}")
        return None

# --- Fungsi Speech-to-Text (Komponen Kustom) ---
def stt_component():
    """Membuat tombol mikrofon yang menggunakan Web Speech API dan mengembalikan teks ke Streamlit."""
    
    # Ambil teks dari session state jika sudah ada
    initial_text = st.session_state.get('stt_text', '')

    html_code = f"""
    <script>
        const stt_button = document.getElementById('stt-mic-button');
        const stt_result = document.getElementById('stt-result');

        // Cek apakah Web Speech API didukung
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {{
            stt_button.innerHTML = '🎤 STT Tidak Didukung';
            stt_button.disabled = true;
            return;
        }}

        const recognition = new SpeechRecognition();
        recognition.continuous = false; // Hanya sekali rekam
        recognition.lang = 'id-ID'; // Bahasa Indonesia

        let isRecording = false;

        stt_button.onclick = () => {{
            if (isRecording) {{
                recognition.stop();
                isRecording = false;
                stt_button.innerHTML = '🎤 Mulai Bicara';
                stt_button.style.backgroundColor = '#4CAF50';
            }} else {{
                recognition.start();
                isRecording = true;
                stt_button.innerHTML = '🔴 Sedang Merekam...';
                stt_button.style.backgroundColor = '#FF0000';
            }}
        }};

        recognition.onresult = (event) => {{
            const transcript = event.results[0][0].transcript;
            // Kirim hasil transcript kembali ke Streamlit
            if (window.parent) {{
                window.parent.postMessage({{
                    streamlit: {{
                        isStreamlit: true,
                        type: "SET_VALUE",
                        value: transcript,
                        id: "stt_text",
                    }}
                }}, "*");
            }}
            stt_button.innerHTML = '🎤 Mulai Bicara';
            stt_button.style.backgroundColor = '#4CAF50';
            isRecording = false;
        }};

        recognition.onerror = (event) => {{
            console.error('Speech recognition error:', event.error);
            stt_button.innerHTML = '🎤 Error! Coba Lagi';
            stt_button.style.backgroundColor = '#FF9800';
            isRecording = false;
        }};
        
        recognition.onend = () => {{
            if (isRecording) {{
                isRecording = false;
                stt_button.innerHTML = '🎤 Mulai Bicara';
                stt_button.style.backgroundColor = '#4CAF50';
            }}
        }};
        
    </script>
    <button id="stt-mic-button" style="
        background-color: #4CAF50;
        color: white;
        padding: 10px 15px;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        font-weight: bold;
        width: 100%;
        transition: background-color 0.3s;
    ">
        🎤 Mulai Bicara
    </button>
    """
    # Menjalankan komponen kustom dan menyimpan hasilnya di st.session_state.stt_text
    html(html_code, height=50, key="stt_html_component")
    return initial_text

# --- 4. Fungsi-Fungsi Manipulasi Chat (Edit & Hapus) ---

def rebuild_chat_session():
    """Membangun kembali sesi chat Gemini dengan riwayat pesan yang tersisa."""
    
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION_PROMPT
    )
    
    if "chat_session" in st.session_state:
        del st.session_state.chat_session
        
    new_chat = st.session_state.gemini_client.chats.create(
        model="gemini-2.5-flash", 
        config=config
    )
    
    contents = []
    for msg in st.session_state.messages:
        parts = []
        if msg["text"]:
            parts.append(types.Part(text=msg["text"]))
        if msg["image_data"]:
            parts.append(types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=base64.b64decode(msg["image_data"]))))
        
        # HANYA masukkan teks dari assistant ke history Gemini
        if parts: 
            if msg["role"] == "user":
                contents.append(types.Content(role="user", parts=parts))
            elif msg["role"] == "assistant" and msg["text"]: 
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
    
    if "generated_image_url" in st.session_state.messages[index]:
        st.session_state.messages[index]["generated_image_url"] = None

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
            # Tampilkan gambar yang diunggah pengguna jika ada
            if msg.get("image_data"):
                display_image_from_base64(msg["image_data"], caption=f"Gambar dari {role_display}")
            
            # Tampilkan gambar yang di-generate oleh AI jika ada
            if msg["role"] == "assistant" and msg.get("generated_image_url"):
                st.image(msg["generated_image_url"], caption="Gambar dari TBC 🖼️", use_column_width=True)
            
            # Tampilkan teks
            if msg.get("text"):
                if msg["role"] == "user":
                    col1, col2, col3 = st.columns([10, 1, 1])
                    with col1:
                        st.markdown(msg["text"])
                    with col2:
                        st.button("❌", key=f"del_{i}", help="Hapus pesan ini", on_click=delete_message, args=(i,))
                    with col3:
                        if st.button("✏️", key=f"edit_btn_{i}", help="Edit pesan ini"):
                            st.session_state.editing_index = i
                            st.rerun() 
                else:
                    st.markdown(msg["text"])
            else:
                # Menangani kasus tanpa teks (hanya gambar upload/generated)
                if msg.get("image_data") and msg["role"] == "user":
                    st.markdown("*Mengirim gambar tanpa teks*")
                elif msg.get("generated_image_url") and msg["role"] == "assistant":
                    st.markdown("*Gambar dihasilkan tanpa teks pendamping*")


# --- 6. Form Edit Pesan (Hanya ditampilkan jika mode edit aktif) ---
if "editing_index" in st.session_state and st.session_state.editing_index >= 0:
    edit_index = st.session_state.editing_index
    current_text = st.session_state.messages[edit_index]["text"]
    
    st.subheader(f"✏️ Edit Pesan ke-{edit_index + 1}")
    
    with st.form(key=f"edit_form_{edit_index}"):
        new_text = st.text_area("Teks Baru:", value=current_text, key="edit_text_area")
        
        if st.session_state.messages[edit_index].get("image_data"):
            display_image_from_base64(st.session_state.messages[edit_index]["image_data"], caption="Gambar asli pesan ini:")
        if st.session_state.messages[edit_index].get("generated_image_url"):
            st.image(st.session_state.messages[edit_index]["generated_image_url"], caption="Gambar yang dihasilkan sebelumnya:")

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

# --- 7. Penanganan Input Chat Baru & Gambar (STT, UPLOAD, GENERATE) ---
# Tambahkan STT component di kolom input
col_stt, col_text_input, col_image_uploader = st.columns([1, 3, 1])

with col_stt:
    stt_text = stt_component() # Panggil komponen STT
    
with col_text_input:
    # Gunakan teks dari STT sebagai nilai awal jika ada
    initial_prompt_value = stt_text if stt_text else ""
    # st.session_state.stt_text harus direset setelah digunakan
    if 'stt_text' in st.session_state and st.session_state.stt_text:
        # PENTING: Jika STT memberikan hasil, pindahkan hasil ke chat_input
        # dan jangan langsung memicu chat_input (yang sudah dipicu oleh stt_component)
        prompt = st.chat_input("Tanyakan sesuatu atau minta saya membuat gambar...", 
                                key="main_chat_input", 
                                value=initial_prompt_value)
        # Hapus stt_text setelah prompt ditampilkan
        del st.session_state.stt_text 
    else:
         prompt = st.chat_input("Tanyakan sesuatu atau minta saya membuat gambar...", 
                                key="main_chat_input")


with col_image_uploader:
    uploaded_image = st.file_uploader("Upload Gambar", type=["jpg", "jpeg", "png"], key="image_uploader")

# Cek apakah ada input (baik dari teks manual, STT, atau gambar upload)
if prompt or uploaded_image or (stt_text and st.session_state.get('stt_text_used') is not True):
    
    # Ambil teks dari prompt atau STT jika baru saja dipicu oleh STT
    user_message_text = prompt if prompt else stt_text
    
    # Cek apakah ini dipicu oleh hasil STT baru yang belum diolah
    is_stt_triggered = (stt_text and st.session_state.get('stt_text_used') is not True)
    
    if is_stt_triggered:
        # Tandai STT sudah digunakan agar tidak terpicu lagi di run berikutnya
        st.session_state.stt_text_used = True 
        
    user_image_data_base64 = get_image_as_base64(uploaded_image)
    
    # Lanjutkan hanya jika ada konten (teks dari prompt/STT atau gambar upload)
    if user_message_text or user_image_data_base64:

        # Flag untuk mengecek apakah user meminta generate gambar
        should_generate_image = False
        if user_message_text:
            lower_prompt = user_message_text.lower()
            if "buat gambar" in lower_prompt or "generate gambar" in lower_prompt or "visualisasikan" in lower_prompt or "gambar" in lower_prompt and len(lower_prompt) > 5:
                should_generate_image = True

        # Tambahkan prompt pengguna dan/atau gambar ke riwayat lokal
        st.session_state.messages.append({
            "role": "user", 
            "text": user_message_text, 
            "image_data": user_image_data_base64,
            "generated_image_url": None
        })
        
        # Tampilkan prompt pengguna segera
        with st.chat_message("user"):
            if user_image_data_base64:
                display_image_from_base64(user_image_data_base64, caption="Gambar Anda")
            if user_message_text:
                st.markdown(user_message_text)
            elif not user_message_text and user_image_data_base64:
                st.markdown("*Mengirim gambar tanpa teks*")


        # --- LOGIKA GENERATE GAMBAR ---
        if should_generate_image:
            image_description = user_message_text.replace("buat gambar", "").replace("generate gambar", "").replace("visualisasikan", "").strip()
            if not image_description:
                image_description = "abstrak"

            with st.spinner(f"🤖 TBC sedang menciptakan gambar '{image_description}'... 🎨"):
                generated_image_url = generate_image_with_dalle(image_description)
                
                if generated_image_url:
                    response_text_ai = "Ini dia gambarnya! 🖼️"
                    st.session_state.messages.append({
                        "role": "assistant",
                        "text": response_text_ai,
                        "image_data": None,
                        "generated_image_url": generated_image_url
                    })
                    
                    with st.chat_message("assistant"):
                        st.markdown(response_text_ai)
                        st.image(generated_image_url, caption="Gambar dari TBC", use_column_width=True)
                else:
                    response_text_ai = "Maaf, TBC gagal membuat gambar kali ini. 😔"
                    st.session_state.messages.append({
                        "role": "assistant",
                        "text": response_text_ai,
                        "image_data": None,
                        "generated_image_url": None
                    })
                    with st.chat_message("assistant"):
                        st.markdown(response_text_ai)
        
        # --- LOGIKA CHAT BIASA (KIRIM KE GEMINI) ---
        else: 
            parts_to_send = []
            if user_message_text:
                parts_to_send.append(types.Part(text=user_message_text))
            if user_image_data_base64:
                parts_to_send.append(types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=base64.b64decode(user_image_data_base64))))
            
            if parts_to_send:
                try:
                    with st.spinner("🤖 TBC sedang menganalisis..."):
                        response = st.session_state.chat_session.send_message(parts_to_send)
                        response_text = response.parts[0].text
                        
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "text": response_text, 
                            "image_data": None,
                            "generated_image_url": None
                        })
                        
                        with st.chat_message("assistant"):
                            st.markdown(response_text)
                            
                except Exception as e:
                    st.error(f"Terjadi kesalahan saat mengirim pesan ke Gemini: {e}")
                    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                        st.session_state.messages.pop() 
            else:
                if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                    st.session_state.messages.pop()
                st.warning("Mohon masukkan teks atau unggah gambar.")

# --- 8. Blok Pengiriman Ulang Otomatis Setelah Edit (SOLUSI RESPONS) ---
if "resend_last_message" in st.session_state and st.session_state.resend_last_message:
    
    st.session_state.resend_last_message = False 
    
    last_user_msg = st.session_state.messages[-1]
    
    # Cek apakah pesan yang diedit adalah permintaan generate gambar
    should_generate_image_on_resend = False
    if last_user_msg["text"]:
        lower_prompt = last_user_msg["text"].lower()
        if "buat gambar" in lower_prompt or "generate gambar" in lower_prompt or "visualisasikan" in lower_prompt or "gambar" in lower_prompt and len(lower_prompt) > 5:
            should_generate_image_on_resend = True

    if should_generate_image_on_resend:
        image_description = last_user_msg["text"].replace("buat gambar", "").replace("generate gambar", "").replace("visualisasikan", "").strip()
        if not image_description:
            image_description = "abstrak"

        with st.spinner(f"🤖 TBC sedang menciptakan ulang gambar '{image_description}'... 🎨"):
            generated_image_url = generate_image_with_dalle(image_description)
            
            if generated_image_url:
                response_text_ai = "Ini dia gambarnya yang baru! 🖼️"
                st.session_state.messages.append({
                    "role": "assistant",
                    "text": response_text_ai,
                    "image_data": None,
                    "generated_image_url": generated_image_url
                })
                
                with st.chat_message("assistant"):
                    st.markdown(response_text_ai)
                    st.image(generated_image_url, caption="Gambar dari TBC", use_column_width=True)
            else:
                response_text_ai = "Maaf, TBC gagal membuat gambar lagi. 😔"
                st.session_state.messages.append({
                    "role": "assistant",
                    "text": response_text_ai,
                    "image_data": None,
                    "generated_image_url": None
                })
                with st.chat_message("assistant"):
                    st.markdown(response_text_ai)
    else: 
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
                    "image_data": None,
                    "generated_image_url": None
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
        "Tombol 🎤 **Mulai Bicara** sekarang tersedia untuk mengirim pesan via suara."
        "\n\nTombol ❌ akan menghapus pesan Anda dan balasan bot."
        "\n\nTombol ✏️ akan memunculkan kotak edit (hanya teks) dan TBC akan **otomatis** merespons pesan yang diedit."
    )
    st.markdown("---")
    st.markdown("Model: **`gemini-2.5-flash` (Multimodal)**")
    st.markdown("Model Gambar: **`DALL-E 3`**")
    st.markdown("Speech-to-Text: **Web Speech API (`id-ID`)**")