import streamlit as st
from streamlit_mic_recorder import mic_recorder
import whisper
from deep_translator import GoogleTranslator
from gtts import gTTS
import os
import base64
import tempfile
import time  # New: Required for unique audio files

# --- 1. APP CONFIGURATION ---
st.set_page_config(page_title="High-Accuracy Translator", layout="wide")

@st.cache_resource
def load_whisper_model():
    # 'small' provides better accuracy for Indian accents
    return whisper.load_model("small")

model = load_whisper_model()

def play_audio(file_path):
    """Encodes audio and forces the browser to play it using a unique key."""
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        # The key="{time.time()}" forces the HTML to refresh so audio plays every time
        md = f"""
            <audio autoplay="true" key="{time.time()}">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)

# --- 2. USER INTERFACE ---
st.title("📞 Tamil ↔ English Voice Bridge (v2.0)")
st.write("Fixed: Audio will now play for every turn in the conversation.")

col1, col2 = st.columns(2)

# --- 3. PERSON 1: TAMIL SPEAKER ---
with col1:
    st.subheader("👤 Person 1 (Tamil)")
    audio_ta = mic_recorder(start_prompt="🎤 Speak Tamil", stop_prompt="⏹️ Stop", key="p1_mic")
    
    if audio_ta:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_ta['bytes'])
            tmp_path = tmp_file.name
        
        try:
            with st.spinner("AI is analyzing Tamil speech..."):
                result = model.transcribe(tmp_path, language="ta")
                ta_text = result['text'].strip()
                
                if ta_text:
                    st.markdown(f"**Heard (Tamil):** {ta_text}")
                    en_translation = GoogleTranslator(source='ta', target='en').translate(ta_text)
                    
                    if en_translation:
                        st.success(f"**To English:** {en_translation}")
                        
                        # UNIQUE FILENAME FIX
                        ts = int(time.time())
                        audio_filename = f"ta_to_en_{ts}.mp3"
                        
                        tts = gTTS(text=en_translation, lang='en')
                        tts.save(audio_filename)
                        play_audio(audio_filename)
                        
                        # Small delay to ensure playback starts before file cleanup
                        time.sleep(1) 
                        os.remove(audio_filename)
                else:
                    st.warning("Could not clearly hear Tamil. Please try again.")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

# --- 4. PERSON 2: ENGLISH SPEAKER ---
with col2:
    st.subheader("👤 Person 2 (English)")
    audio_en = mic_recorder(start_prompt="🎤 Speak English", stop_prompt="⏹️ Stop", key="p2_mic")
    
    if audio_en:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_en['bytes'])
            tmp_path = tmp_file.name
            
        try:
            with st.spinner("AI is analyzing English speech..."):
                result = model.transcribe(tmp_path, language="en")
                en_text = result['text'].strip()
                
                if en_text:
                    st.markdown(f"**Heard (English):** {en_text}")
                    ta_translation = GoogleTranslator(source='en', target='ta').translate(en_text)
                    
                    if ta_translation:
                        st.success(f"**To Tamil:** {ta_translation}")
                        
                        # UNIQUE FILENAME FIX
                        ts = int(time.time())
                        audio_filename = f"en_to_ta_{ts}.mp3"
                        
                        tts = gTTS(text=ta_translation, lang='ta')
                        tts.save(audio_filename)
                        play_audio(audio_filename)
                        
                        time.sleep(1)
                        os.remove(audio_filename)
                else:
                    st.warning("Could not clearly hear English. Please try again.")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)




