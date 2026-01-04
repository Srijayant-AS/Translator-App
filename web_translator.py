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
st.set_page_config(page_title="Self-Erasing Tamil-English Bridge", layout="wide")

@st.cache_resource
def load_whisper_model():
    return whisper.load_model("small")

model = load_whisper_model()

def play_audio(file_path):
    """Encodes and plays audio."""
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        
    audio_html = f"""
        <audio autoplay="true">
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)

# --- 2. USER INTERFACE ---
st.title("📞 Tamil ↔ English Voice Bridge")
st.write("The translation will disappear automatically after the audio plays.")

col1, col2 = st.columns(2)

# --- 3. PERSON 1: TAMIL SPEAKER ---
with col1:
    st.subheader("👤 Person 1 (Tamil)")
    audio_ta = mic_recorder(start_prompt="🎤 Speak Tamil", stop_prompt="⏹️ Stop", key="ta_mic_erase")
    
    if audio_ta:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_ta['bytes'])
            tmp_path = tmp_file.name
        
        try:
            with st.spinner("Processing..."):
                result = model.transcribe(tmp_path, language="ta", initial_prompt="வணக்கம், எப்படி இருக்கீங்க?")
                ta_text = result['text'].strip()
                
                if ta_text:
                    st.write(f"**Heard:** {ta_text}")
                    en_translation = GoogleTranslator(source='ta', target='en').translate(ta_text)
                    st.success(f"**English:** {en_translation}")
                    
                    # Audio generation
                    fname = f"ta_en_{int(time.time())}.mp3"
                    gTTS(text=en_translation, lang='en').save(fname)
                    play_audio(fname)
                    
                    # --- THE AUTO-DELETE LOGIC ---
                    # Wait for 5 seconds so they can read/hear it
                    time.sleep(5) 
                    os.remove(fname)
                    # Refresh the page to clear the text
                    st.rerun() 
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)

# --- 4. PERSON 2: ENGLISH SPEAKER ---
with col2:
    st.subheader("👤 Person 2 (English)")
    audio_en = mic_recorder(start_prompt="🎤 Speak English", stop_prompt="⏹️ Stop", key="en_mic_erase")
    
    if audio_en:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_en['bytes'])
            tmp_path = tmp_file.name
            
        try:
            with st.spinner("Processing..."):
                result = model.transcribe(tmp_path, language="en")
                en_text = result['text'].strip()
                
                if en_text:
                    st.write(f"**Heard:** {en_text}")
                    ta_translation = GoogleTranslator(source='en', target='ta').translate(en_text)
                    st.success(f"**Tamil:** {ta_translation}")
                    
                    # Audio generation
                    fname = f"en_ta_{int(time.time())}.mp3"
                    gTTS(text=ta_translation, lang='ta').save(fname)
                    play_audio(fname)
                    
                    # --- THE AUTO-DELETE LOGIC ---
                    # Wait for 5 seconds
                    time.sleep(3) 
                    os.remove(fname)
                    # Refresh the page to clear the text
                    st.rerun()
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)








