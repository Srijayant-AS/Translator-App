import streamlit as st
from streamlit_mic_recorder import mic_recorder
import whisper
from googletrans import Translator
from gtts import gTTS
import os
import base64

# --- SETTINGS & MODELS ---
st.set_page_config(page_title="Tamil-Kannada Intercom", layout="wide")
translator = Translator()

@st.cache_resource
def load_whisper():
    return whisper.load_model("base")

model = load_whisper()

def autoplay_audio(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)

# --- APP INTERFACE ---
st.title("🗣️ Tamil ↔️ Kannada Real-Time Translator")
st.write("Speaker A speaks Tamil. Speaker B speaks Kannada. The system translates and speaks back.")

col1, col2 = st.columns(2)

# --- SPEAKER A: TAMIL ---
with col1:
    st.header("Tamil Speaker")
    audio_tamil = mic_recorder(start_prompt="🎤 Speak Tamil", stop_prompt="Stop", key="tamil_mic")
    
    if audio_tamil:
        # Save and Transcribe
        with open("temp_tamil.wav", "wb") as f:
            f.write(audio_tamil['bytes'])
        
        with st.spinner("Translating Tamil to Kannada..."):
            result = model.transcribe("temp_tamil.wav")
            tamil_text = result['text']
            st.info(f"Detected Tamil: {tamil_text}")
            
            # Translate to Kannada
            translated = translator.translate(tamil_text, src='ta', dest='kn').text
            st.success(f"To Kannada: {translated}")
            
            # Speak back in Kannada
            tts = gTTS(text=translated, lang='kn')
            tts.save("reply_kn.mp3")
            autoplay_audio("reply_kn.mp3")

# --- SPEAKER B: KANNADA ---
with col2:
    st.header("Kannada Speaker")
    audio_kannada = mic_recorder(start_prompt="🎤 Speak Kannada", stop_prompt="Stop", key="kannada_mic")
    
    if audio_kannada:
        with open("temp_kn.wav", "wb") as f:
            f.write(audio_kannada['bytes'])
            
        with st.spinner("Translating Kannada to Tamil..."):
            result = model.transcribe("temp_kn.wav")
            kannada_text = result['text']
            st.info(f"Detected Kannada: {kannada_text}")
            
            # Translate to Tamil
            translated = translator.translate(kannada_text, src='kn', dest='ta').text
            st.success(f"To Tamil: {translated}")
            
            # Speak back in Tamil
            tts = gTTS(text=translated, lang='ta')
            tts.save("reply_ta.mp3")
            autoplay_audio("reply_ta.mp3")