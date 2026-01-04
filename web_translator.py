import streamlit as st
from streamlit_mic_recorder import mic_recorder
import whisper
from deep_translator import GoogleTranslator
from gtts import gTTS
import os
import base64
import tempfile
import time

# --- 1. APP CONFIGURATION ---
st.set_page_config(page_title="Stable Voice Bridge", layout="wide")

# Load Whisper model (Small for better accuracy)
@st.cache_resource
def load_whisper_model():
    return whisper.load_model("small")

model = load_whisper_model()

# Use Session State to manage turns and prevent infinite loops
if 'process_complete' not in st.session_state:
    st.session_state.process_complete = False

def play_audio(file_path):
    """Encodes and plays audio."""
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
    audio_html = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    st.markdown(audio_html, unsafe_allow_html=True)

# --- 2. USER INTERFACE ---
st.title("📞 Tamil ↔ English Voice Bridge")
st.write("Each side resets automatically after 2 seconds.")

col1, col2 = st.columns(2)

# --- 3. PERSON 1: TAMIL SPEAKER ---
with col1:
    st.subheader("👤 Person 1 (Tamil)")
    # We change the key every time to force a fresh microphone
    ta_key = "ta_mic_" + str(st.session_state.get('ta_version', 0))
    audio_ta = mic_recorder(start_prompt="🎤 Speak Tamil", stop_prompt="⏹️ Stop", key=ta_key)
    
    if audio_ta:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_ta['bytes'])
            tmp_path = tmp_file.name
        
        try:
            with st.spinner("Processing Tamil..."):
                result = model.transcribe(tmp_path, language="ta", initial_prompt="வணக்கம், எப்படி இருக்கீங்க?")
                ta_text = result['text'].strip()
                
                if ta_text:
                    st.write(f"**Heard:** {ta_text}")
                    en_trans = GoogleTranslator(source='ta', target='en').translate(ta_text)
                    st.success(f"**English:** {en_trans}")
                    
                    fname = f"ta_en_{int(time.time())}.mp3"
                    gTTS(text=en_trans, lang='en').save(fname)
                    play_audio(fname)
                    
                    time.sleep(2)
                    os.remove(fname)
                    # Update version to reset mic and rerun
                    st.session_state.ta_version = st.session_state.get('ta_version', 0) + 1
                    st.rerun()
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)

# --- 4. PERSON 2: ENGLISH SPEAKER ---
with col2:
    st.subheader("👤 Person 2 (English)")
    en_key = "en_mic_" + str(st.session_state.get('en_version', 0))
    audio_en = mic_recorder(start_prompt="🎤 Speak English", stop_prompt="⏹️ Stop", key=en_key)
    
    if audio_en:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_en['bytes'])
            tmp_path = tmp_file.name
            
        try:
            with st.spinner("Processing English..."):
                result = model.transcribe(tmp_path, language="en")
                en_text = result['text'].strip()
                
                if en_text:
                    st.write(f"**Heard:** {en_text}")
                    ta_trans = GoogleTranslator(source='en', target='ta').translate(en_text)
                    st.success(f"**Tamil:** {ta_trans}")
                    
                    fname = f"en_ta_{int(time.time())}.mp3"
                    gTTS(text=ta_trans, lang='ta').save(fname)
                    play_audio(fname)
                    
                    time.sleep(2)
                    os.remove(fname)
                    # Update version to reset mic and rerun
                    st.session_state.en_version = st.session_state.get('en_version', 0) + 1
                    st.rerun()
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)










