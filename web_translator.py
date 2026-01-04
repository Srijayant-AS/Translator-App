import streamlit as st
from streamlit_mic_recorder import mic_recorder
import whisper
from deep_translator import GoogleTranslator
from gtts import gTTS
import os
import base64
import tempfile

# --- 1. APP CONFIGURATION ---
st.set_page_config(page_title="Tamil-English Call", layout="wide")

@st.cache_resource
def load_whisper_model():
    # 'base' is the best balance of speed and accuracy for Indian accents
    return whisper.load_model("base")

model = load_whisper_model()

def play_audio(file_path):
    """Automatically plays the generated audio in the user's browser."""
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)

# --- 2. USER INTERFACE ---
st.title("📞 Tamil ↔ English Voice Bridge")
st.write("A real-time walkie-talkie for people speaking different languages.")

col1, col2 = st.columns(2)

# --- 3. PERSON 1: TAMIL SPEAKER ---
with col1:
    st.subheader("👤 Person 1 (Tamil)")
    st.info("பேசுவதற்கு கீழே உள்ள பட்டனை அழுத்தவும் (Click below to speak Tamil)")
    audio_ta = mic_recorder(start_prompt="🎤 Speak Tamil", stop_prompt="⏹️ Stop", key="p1_mic")
    
    if audio_ta:
        # Step A: Save audio to a temporary file safely
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_ta['bytes'])
            tmp_path = tmp_file.name
        
        try:
            with st.spinner("Hearing Tamil..."):
                # Step B: Speech to Text
                result = model.transcribe(tmp_path)
                ta_text = result['text'].strip()
                
                if ta_text:
                    st.markdown(f"**Heard (Tamil):** {ta_text}")
                    
                    # Step C: Translate to English
                    en_translation = GoogleTranslator(source='ta', target='en').translate(ta_text)
                    
                    if en_translation:
                        st.success(f"**To English:** {en_translation}")
                        
                        # Step D: Text to Speech (English)
                        tts = gTTS(text=en_translation, lang='en')
                        tts.save("p1_out.mp3")
                        play_audio("p1_out.mp3")
                else:
                    st.warning("No speech detected. Please speak louder or closer to the mic.")
        finally:
            # Step E: Clean up the file to prevent server clutter
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

# --- 4. PERSON 2: ENGLISH SPEAKER ---
with col2:
    st.subheader("👤 Person 2 (English)")
    st.info("Click the button below to reply in English")
    audio_en = mic_recorder(start_prompt="🎤 Speak English", stop_prompt="⏹️ Stop", key="p2_mic")
    
    if audio_en:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_en['bytes'])
            tmp_path = tmp_file.name
            
        try:
            with st.spinner("Hearing English..."):
                result = model.transcribe(tmp_path)
                en_text = result['text'].strip()
                
                if en_text:
                    st.markdown(f"**Heard (English):** {en_text}")
                    
                    # Translate to Tamil
                    ta_translation = GoogleTranslator(source='en', target='ta').translate(en_text)
                    
                    if ta_translation:
                        st.success(f"**To Tamil:** {ta_translation}")
                        
                        # Text to Speech (Tamil)
                        tts = gTTS(text=ta_translation, lang='ta')
                        tts.save("p2_out.mp3")
                        play_audio("p2_out.mp3")
                else:
                    st.warning("No speech detected. Please try again.")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
           


