import streamlit as st
from streamlit_mic_recorder import mic_recorder
import whisper
from deep_translator import GoogleTranslator
from gtts import gTTS
import os
import base64

# --- APP CONFIG ---
st.set_page_config(page_title="Tamil-English Call", layout="wide")

@st.cache_resource
def load_whisper():
    return whisper.load_model("base")

model = load_whisper()

def play_audio(file_path):
    """Automatically plays the audio file in the browser."""
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)

# --- UI DESIGN ---
st.title("📞 Tamil ↔ English Voice Bridge")
st.info("How to use: Person 1 uses the left side. Person 2 uses the right side.")

col1, col2 = st.columns(2)

# --- PERSON 1: TAMIL SPEAKER ---
with st.spinner("Translating to English for Person 2..."):
            result = model.transcribe("p1_input.wav")
            ta_text = result['text'].strip() # .strip() removes empty spaces
            
            if ta_text: # <--- SAFETY GUARD: Only proceed if text exists
                st.markdown(f"**Heard (Tamil):** {ta_text}")
                en_translation = GoogleTranslator(source='ta', target='en').translate(ta_text)
                
                if en_translation: # <--- SECOND GUARD
                    st.success(f"**Translated (English):** {en_translation}")
                    tts_en = gTTS(text=en_translation, lang='en')
                    tts_en.save("p1_out.mp3")
                    play_audio("p1_out.mp3")
            else:
                st.warning("I didn't hear anything. Please try speaking again!")

# --- PERSON 2: ENGLISH SPEAKER ---
with st.spinner("Translating to Tamil for Person 1..."):
            result = model.transcribe("p2_input.wav")
            en_text = result['text'].strip()
            
            if en_text: # <--- SAFETY GUARD
                st.markdown(f"**Heard (English):** {en_text}")
                ta_translation = GoogleTranslator(source='en', target='ta').translate(en_text)
                
                if ta_translation: # <--- SECOND GUARD
                    st.success(f"**Translated (Tamil):** {ta_translation}")
                    tts_ta = gTTS(text=ta_translation, lang='ta')
                    tts_ta.save("p2_out.mp3")
                    play_audio("p2_out.mp3")
            else:
                st.warning("I didn't hear anything. Please try speaking again!")
           

