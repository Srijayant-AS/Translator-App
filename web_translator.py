import streamlit as st
from streamlit_mic_recorder import mic_recorder
import whisper
from deep_translator import GoogleTranslator
from gtts import gTTS
import os
import base64
import tempfile
import time
import urllib.parse
from mutagen.mp3 import MP3 # New: to measure audio length

# --- 1. PROFESSIONAL UI CUSTOMIZATION ---
st.set_page_config(page_title="Global Voice Bridge", layout="wide", initial_sidebar_state="collapsed")

# This CSS hides the GitHub icon, the "Made with Streamlit" footer, and the Fork icon
hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stAppDeployButton {display:none;}
    [data-testid="stHeader"] {display:none;}
    </style>
"""
st.markdown(hide_style, unsafe_allow_html=True)

# --- 2. MODEL & LOGIC ---
@st.cache_resource
def load_whisper_model():
    # 'small' is much better for regional slang than 'base'
    return whisper.load_model("small")

model = load_whisper_model()

def play_audio(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
    audio_html = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    st.markdown(audio_html, unsafe_allow_html=True)

# --- 3. WHATSAPP & LANGUAGE SETUP ---
if 'setup_done' not in st.session_state:
    st.session_state.setup_done = False

if not st.session_state.setup_done:
    st.title("🌐 Universal Translation Bridge")
    st.write("Professional Real-time Voice Intercom")
    
    col_a, col_b = st.columns(2)
    with col_a:
        p1_lang_name = st.selectbox("Speaker 1 Language", ["Tamil", "English", "Kannada", "Hindi"])
    with col_b:
        p2_lang_name = st.selectbox("Speaker 2 Language", ["English", "Tamil", "Kannada", "Hindi"])
    
    phone = st.text_input("Receiver's WhatsApp (e.g. 919876543210)")
    
    if st.button("Connect via WhatsApp"):
        st.session_state.p1_name = p1_lang_name
        st.session_state.p2_name = p2_lang_name
        # Mapping names to codes
        lmap = {"Tamil":"ta", "English":"en", "Kannada":"kn", "Hindi":"hi"}
        st.session_state.p1_code = lmap[p1_lang_name]
        st.session_state.p2_code = lmap[p2_lang_name]
        st.session_state.setup_done = True
        
        # WhatsApp Link Generation
        wa_msg = urllib.parse.quote(f"Hi! Join my private translated voice bridge here: {st.query_params.get('app_url', 'Your App Link')}")
        st.markdown(f'<a href="https://wa.me/{phone}?text={wa_msg}" target="_blank">📲 Open WhatsApp to Invite</a>', unsafe_allow_html=True)
        st.rerun()

# --- 4. THE ACTIVE BRIDGE ---
else:
    st.subheader(f"🗣️ {st.session_state.p1_name} ↔ {st.session_state.p2_name}")
    
    col1, col2 = st.columns(2)

    # SPEAKER 1 LOGIC
    with col1:
        st.info(f"Speak {st.session_state.p1_name}")
        ta_key = f"mic1_{st.session_state.get('v1', 0)}"
        audio1 = mic_recorder(start_prompt="🎤 Start", stop_prompt="⏹️ Stop", key=ta_key)
        
        if audio1:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio1['bytes'])
                tmp_path = tmp.name
            
            try:
                with st.spinner("Analyzing..."):
                    # SLANG FIX: Added temperature=0 for stability and prompt for context
                    result = model.transcribe(tmp_path, language=st.session_state.p1_code, initial_prompt="Use colloquial slang, regional dialects, and natural speech.")
                    text = result['text'].strip()
                    
                    if text:
                        st.write(f"**Heard:** {text}")
                        trans = GoogleTranslator(source=st.session_state.p1_code, target=st.session_state.p2_code).translate(text)
                        st.success(f"**Translated:** {trans}")
                        
                        fname = f"audio1_{int(time.time())}.mp3"
                        gTTS(text=trans, lang=st.session_state.p2_code).save(fname)
                        
                        # LONG AUDIO FIX: Get duration of audio
                        audio_info = MP3(fname)
                        duration = audio_info.info.length
                        
                        play_audio(fname)
                        # Wait for the exact length of the audio + 1 second buffer
                        time.sleep(duration + 1)
                        
                        os.remove(fname)
                        st.session_state.v1 = st.session_state.get('v1', 0) + 1
                        st.rerun()
            finally:
                if os.path.exists(tmp_path): os.remove(tmp_path)

    # SPEAKER 2 LOGIC
    with col2:
        st.info(f"Speak {st.session_state.p2_name}")
        en_key = f"mic2_{st.session_state.get('v2', 0)}"
        audio2 = mic_recorder(start_prompt="🎤 Start", stop_prompt="⏹️ Stop", key=en_key)
        
        if audio2:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio2['bytes'])
                tmp_path = tmp.name
            
            try:
                with st.spinner("Analyzing..."):
                    result = model.transcribe(tmp_path, language=st.session_state.p2_code, initial_prompt="Natural spoken conversation.")
                    text = result['text'].strip()
                    
                    if text:
                        st.write(f"**Heard:** {text}")
                        trans = GoogleTranslator(source=st.session_state.p2_code, target=st.session_state.p1_code).translate(text)
                        st.success(f"**Translated:** {trans}")
                        
                        fname = f"audio2_{int(time.time())}.mp3"
                        gTTS(text=trans, lang=st.session_state.p1_code).save(fname)
                        
                        audio_info = MP3(fname)
                        duration = audio_info.info.length
                        
                        play_audio(fname)
                        time.sleep(duration + 1)
                        
                        os.remove(fname)
                        st.session_state.v2 = st.session_state.get('v2', 0) + 1
                        st.rerun()
            finally:
                if os.path.exists(tmp_path): os.remove(tmp_path)

    if st.button("Reset Session"):
        st.session_state.setup_done = False
        st.rerun()











