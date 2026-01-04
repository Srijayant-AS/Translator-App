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
st.set_page_config(page_title="Tamil-English Bridge", layout="wide")

@st.cache_resource
def load_whisper_model():
    return whisper.load_model("small")

model = load_whisper_model()

def play_audio(file_path):
    """Plays audio and deletes the file afterward."""
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        
    audio_html = f"""
        <audio autoplay="true" key="{time.time()}">
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)

# --- 2. USER INTERFACE ---
st.title("📞 Tamil ↔ English Voice Bridge")
st.write("The history clears automatically as soon as the other person speaks.")

col1, col2 = st.columns(2)

# --- 3. CONTAINERS FOR AUTO-ERASING ---
# We create these so we can clear them individually
with col1:
    st.subheader("👤 Person 1 (Tamil)")
    ta_mic_area = st.empty() # Placeholder for the mic
    ta_text_area = st.empty() # Placeholder for the translated text

with col2:
    st.subheader("👤 Person 2 (English)")
    en_mic_area = st.empty() # Placeholder for the mic
    en_text_area = st.empty() # Placeholder for the translated text

# --- 4. LOGIC FOR TAMIL SPEAKER ---
with ta_mic_area:
    audio_ta = mic_recorder(start_prompt="🎤 Speak Tamil", stop_prompt="⏹️ Stop", key="ta_mic")

if audio_ta:
    # STEP 1: IMMEDIATELY ERASE BOTH SIDES' HISTORY
    ta_text_area.empty()
    en_text_area.empty()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        tmp_file.write(audio_ta['bytes'])
        tmp_path = tmp_file.name
    
    try:
        with ta_text_area.container(): # Put new text here
            with st.spinner("Translating..."):
                result = model.transcribe(tmp_path, language="ta", initial_prompt="வணக்கம், எப்படி இருக்கீங்க?")
                ta_text = result['text'].strip()
                
                if ta_text:
                    st.write(f"**Heard:** {ta_text}")
                    en_translation = GoogleTranslator(source='ta', target='en').translate(ta_text)
                    st.success(f"**English:** {en_translation}")
                    
                    # Generate and play audio
                    fname = f"out_{int(time.time())}.mp3"
                    gTTS(text=en_translation, lang='en').save(fname)
                    play_audio(fname)
                    time.sleep(1)
                    os.remove(fname)
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

# --- 5. LOGIC FOR ENGLISH SPEAKER ---
with en_mic_area:
    audio_en = mic_recorder(start_prompt="🎤 Speak English", stop_prompt="⏹️ Stop", key="en_mic")

if audio_en:
    # STEP 1: IMMEDIATELY ERASE BOTH SIDES' HISTORY
    ta_text_area.empty()
    en_text_area.empty()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        tmp_file.write(audio_en['bytes'])
        tmp_path = tmp_file.name
        
    try:
        with en_text_area.container(): # Put new text here
            with st.spinner("Translating..."):
                result = model.transcribe(tmp_path, language="en")
                en_text = result['text'].strip()
                
                if en_text:
                    st.write(f"**Heard:** {en_text}")
                    ta_translation = GoogleTranslator(source='en', target='ta').translate(en_text)
                    st.success(f"**Tamil:** {ta_translation}")
                    
                    # Generate and play audio
                    fname = f"out_{int(time.time())}.mp3"
                    gTTS(text=ta_translation, lang='ta').save(fname)
                    play_audio(fname)
                    time.sleep(1)
                    os.remove(fname)
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)







