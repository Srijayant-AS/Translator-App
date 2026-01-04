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
    # 'small' is much better at understanding colloquial/spoken accents
    return whisper.load_model("small")

model = load_whisper_model()

def play_audio(file_path):
    """Encodes audio and forces the browser to play it."""
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio autoplay="true" key="{time.time()}">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)

# --- 2. USER INTERFACE ---
st.title("📞 Tamil ↔ English Voice Bridge (v3.0)")
st.caption("Now supports spoken/colloquial Tamil. Previous text clears automatically on new recording.")

# Create placeholders for dynamic clearing
p1_container = st.container()
p2_container = st.container()

col1, col2 = st.columns(2)

# --- 3. PERSON 1: TAMIL SPEAKER ---
with col1:
    st.subheader("👤 Person 1 (Tamil)")
    # 'key' is crucial; changing it or interacting resets the view
    audio_ta = mic_recorder(start_prompt="🎤 Speak Tamil", stop_prompt="⏹️ Stop", key="p1_mic_v3")
    
    # Placeholder to show/clear text
    ta_output = st.empty()
    
    if audio_ta:
        # Immediately clear the previous session's display
        ta_output.empty()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_ta['bytes'])
            tmp_path = tmp_file.name
        
        try:
            with st.spinner("Decoding spoken Tamil..."):
                # COLLOQUIAL FIX: We use 'initial_prompt' to guide Whisper 
                # to accept spoken/slang Tamil patterns.
                result = model.transcribe(
                    tmp_path, 
                    language="ta", 
                    initial_prompt="வணக்கம், எப்படி இருக்கீங்க? சாப்பிட்டீங்களா?"
                )
                ta_text = result['text'].strip()
                
                if ta_text:
                    with ta_output.container():
                        st.markdown(f"**Heard (Tamil):** {ta_text}")
                        en_translation = GoogleTranslator(source='ta', target='en').translate(ta_text)
                        
                        if en_translation:
                            st.success(f"**To English:** {en_translation}")
                            
                            ts = int(time.time())
                            audio_filename = f"ta_to_en_{ts}.mp3"
                            tts = gTTS(text=en_translation, lang='en')
                            tts.save(audio_filename)
                            play_audio(audio_filename)
                            
                            time.sleep(1.5) # Give it time to play
                            os.remove(audio_filename)
                else:
                    st.warning("I couldn't catch that. Please try again.")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

# --- 4. PERSON 2: ENGLISH SPEAKER ---
with col2:
    st.subheader("👤 Person 2 (English)")
    audio_en = mic_recorder(start_prompt="🎤 Speak English", stop_prompt="⏹️ Stop", key="p2_mic_v3")
    
    en_output = st.empty()
    
    if audio_en:
        en_output.empty() # Clear history
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_en['bytes'])
            tmp_path = tmp_file.name
            
        try:
            with st.spinner("Decoding English..."):
                result = model.transcribe(tmp_path, language="en")
                en_text = result['text'].strip()
                
                if en_text:
                    with en_output.container():
                        st.markdown(f"**Heard (English):** {en_text}")
                        ta_translation = GoogleTranslator(source='en', target='ta').translate(en_text)
                        
                        if ta_translation:
                            st.success(f"**To Tamil:** {ta_translation}")
                            
                            ts = int(time.time())
                            audio_filename = f"en_to_ta_{ts}.mp3"
                            tts = gTTS(text=ta_translation, lang='ta')
                            tts.save(audio_filename)
                            play_audio(audio_filename)
                            
                            time.sleep(1.5)
                            os.remove(audio_filename)
                else:
                    st.warning("No speech detected.")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)





