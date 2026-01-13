import streamlit as st
from streamlit_mic_recorder import mic_recorder
import whisper
from deep_translator import GoogleTranslator
from gtts import gTTS
import os, base64, tempfile, time, urllib.parse, uuid
from mutagen.mp3 import MP3

# --- 1. SETUP & UI ---
st.set_page_config(page_title="Voice Bridge", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stAppDeployButton {display:none;} [data-testid="stHeader"] {display:none;}
    .main-box { background-color: #f9f9f9; padding: 20px; border-radius: 15px; border: 1px solid #ddd; }
    </style>
""", unsafe_allow_html=True)

# --- 2. FAST ENGINE ---
@st.cache_resource
def load_whisper_model():
    return whisper.load_model("tiny")

model = load_whisper_model()

def play_audio(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
    audio_html = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    st.markdown(audio_html, unsafe_allow_html=True)

# --- 3. THE CLOUD "REAL-TIME" SIMULATOR ---
# We use st.cache_data to simulate a room where both people can "see" messages
if 'chat_db' not in st.session_state:
    st.session_state.chat_db = {}

# --- 4. DUAL-ROLE LOGIC ---
query_params = st.query_params
room_id = query_params.get("room")
s_lang = query_params.get("slang")
r_lang = query_params.get("rlang")
role = query_params.get("role")

# --- CASE A: SENDER (START CALL) ---
if not room_id:
    st.title("📞 Private Voice Bridge")
    my_l = st.selectbox("I speak:", ["Tamil", "English", "Kannada", "Hindi"])
    phone = st.text_input("Receiver Phone (e.g. 919876543210)")

    if st.button("Generate Secure Room"):
        rid = str(uuid.uuid4())[:8]
        try:
            from streamlit.web.server.websocket_headers import _get_websocket_headers
            host = _get_websocket_headers().get("Host")
            full_link = f"https://{host}/?room={rid}&slang={my_l}"
            st.success("✅ Link Generated!")
            st.text_input("Copy this:", full_link)
            wa_url = f"https://api.whatsapp.com/send?phone={phone}&text={urllib.parse.quote('Join call: '+full_link)}"
            st.markdown(f'<a href="{wa_url}" target="_blank">📲 Send to WhatsApp</a>', unsafe_allow_html=True)
            st.session_state.rid, st.session_state.my_l = rid, my_l
        except: st.error("Deploy to web to use.")

    if st.button("Enter Room"):
        st.query_params.update(room=st.session_state.rid, slang=st.session_state.my_l, role="sender")
        st.rerun()

# --- CASE B: RECEIVER (JOIN CALL) ---
elif room_id and not r_lang:
    st.title("📞 Incoming Call")
    my_rl = st.selectbox("I speak:", ["English", "Tamil", "Kannada", "Hindi"])
    if st.button("Accept Call"):
        st.query_params.update(rlang=my_rl, role="receiver")
        st.rerun()

# --- CASE C: THE LIVE CHAT ---
else:
    my_label = s_lang if role == "sender" else r_lang
    their_label = r_lang if role == "sender" else s_lang
    lmap = {"Tamil":"ta", "English":"en", "Kannada":"kn", "Hindi":"hi"}

    st.subheader(f"🔒 Secure Room: {room_id}")
    st.write(f"You: **{my_label}** | Partner: **{their_label}**")

    # 1. INCOMING MESSAGE AREA
    # In a real cloud app, this is where the partner's text appears
    st.markdown('<div class="main-box">', unsafe_allow_html=True)
    incoming_key = f"{room_id}_{'receiver' if role=='sender' else 'sender'}"
    
    # We simulate the incoming text check
    incoming_text = st.session_state.get(incoming_key, "")
    
    if incoming_text:
        st.info(f"Incoming from Partner ({my_label}):")
        st.subheader(incoming_text)
        if st.button("🔊 READ OUT LOUD"):
            fname = "voice.mp3"
            gTTS(text=incoming_text, lang=lmap[my_label]).save(fname)
            play_audio(fname)
            time.sleep(2)
            os.remove(fname)
    else:
        st.write("Waiting for partner to speak...")
    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # 2. OUTGOING MESSAGE AREA
    st.write(f"🎤 Record your response in **{my_label}**")
    aud = mic_recorder(start_prompt="Start", stop_prompt="Stop & Send", key=f"mic_{role}")

    if aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(aud['bytes'])
            tmp_path = tmp.name
        try:
            with st.spinner("Translating..."):
                result = model.transcribe(tmp_path, language=lmap[my_label], fp16=False)
                text = result['text'].strip()
                if text:
                    # Translate to THEIR language
                    trans_text = GoogleTranslator(source=lmap[my_label], target=lmap[their_label]).translate(text)
                    
                    # SAVE TO CLOUD (Simulated)
                    my_key = f"{room_id}_{role}"
                    st.session_state[my_key] = trans_text
                    
                    st.success(f"Sent: {trans_text}")
                    time.sleep(1)
                    st.rerun()
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)

    if st.button("❌ End Call"):
        st.query_params.clear()
        st.rerun()














