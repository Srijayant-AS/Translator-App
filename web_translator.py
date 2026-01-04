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

# Initialize Session State to keep track of audio playing
if 'last_played' not in st.session_state:
    st.session_state.last_played = None

@st.cache_resource
def load_whisper_model():
    return whisper.load_model("small")

model = load_whisper_model()

def play_audio(file_path, speaker_id):
    """Plays audio only if it's the current turn."""
    # Create a unique ID for this specific translation turn
    turn_id = f"{speaker_id}_{time.time()}"
    
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        
    # We use a unique key and only render this if it hasn't been played
    audio_html = f"""
        <audio autoplay="true" key="{turn_id}">
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)

# --- 2. USER INTERFACE ---
st.title("📞 Tamil ↔ English Voice Bridge")
st.caption("Clean-Turn Logic: Audio only plays once per translation.")

col1, col2 = st.columns(2)

# --- 3. PERSON 1: TAMIL SPEAKER (Produces English Audio) ---
with col1:
    st.subheader("👤 Person 1 (Tamil)")
    # Using a unique key for the mic helps reset the state
    audio_ta = mic_recorder(start_prompt="🎤 Speak Tamil", stop_prompt="⏹️ Stop", key="mic_tamil")
    
    if audio_ta:
        # Step A: Clear previous session state for the other speaker
        st.session_state.last_played = "tamil_turn"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_ta['bytes'])
            tmp_path = tmp_file.name
        
        try:
            with st.spinner("Translating to English..."):
                result = model.transcribe(tmp_path, language="ta", initial_prompt="வணக்கம், எப்படி இருக்கீங்க?")
                ta_text = result['text'].strip()
                
                if ta_text:
                    st.write(f"**Heard:** {ta_text}")
                    en_translation = GoogleTranslator(source='ta', target='en').translate(ta_text)
                    st.success(f"**English:** {en_translation}")
                    
                    # Generate unique audio
                    ts = int(time.time())
                    filename = f"out_en_{ts}.mp3"
                    tts = gTTS(text=en_translation, lang='en')
                    tts.save(filename)
                    
                    # Play English audio for Person 2
                    play_audio(filename, "p1")
                    
                    time.sleep(1)
                    os.remove(filename)
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)

# --- 4. PERSON 2: ENGLISH SPEAKER (Produces Tamil Audio) ---
with col2:
    st.subheader("👤 Person 2 (English)")
    audio_en = mic_recorder(start_prompt="🎤 Speak English", stop_prompt="⏹️ Stop", key="mic_english")
    
    if audio_en:
        # Step A: Clear previous session state for the other speaker
        st.session_state.last_played = "english_turn"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_en['bytes'])
            tmp_path = tmp_file.name
            
        try:
            with st.spinner("Translating to Tamil..."):
                result = model.transcribe(tmp_path, language="en")
                en_text = result['text'].strip()
                
                if en_text:
                    st.write(f"**Heard:** {en_text}")
                    ta_translation = GoogleTranslator(source='en', target='ta').translate(en_text)
                    st.success(f"**Tamil:** {ta_translation}")
                    
                    # Generate unique audio
                    ts = int(time.time())
                    filename = f"out_ta_{ts}.mp3"
                    tts = gTTS(text=ta_translation, lang='ta')
                    tts.save(filename)
                    
                    # Play Tamil audio for Person 1
                    play_audio(filename, "p2")
                    
                    time.sleep(1)
                    os.remove(filename)
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)






