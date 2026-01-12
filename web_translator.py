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
from mutagen.mp3 import MP3

# --- 1. PROFESSIONAL UI & BRANDING ---
st.set_page_config(page_title="AI Voice Bridge", layout="wide")

# Hide Streamlit Branding
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stAppDeployButton {display:none;}
    </style>
""", unsafe_allow_html=True)

# --- 2. FAST MODEL LOADING ---
@st.cache_resource
def load_whisper_model():
    # 'small' is used for slang accuracy; for max speed 'base' is faster 
    # but 'small' is better for your slang requirement.
    return whisper.load_model("small")

model = load_whisper_model()

def play_audio(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
    audio_html = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    st.markdown(audio_html, unsafe_allow_html=True)

# --- 3. CALL SETUP & WHATSAPP LOGIC ---
if 'call_active' not in st.session_state:
    st.session_state.call_active = False

if not st.session_state.call_active:
    st.title("📞 AI Voice Bridge Setup")
    
    # 1. User selects their own language
    my_lang = st.selectbox("I will speak in:", ["Tamil", "English", "Kannada", "Hindi"])
    
    # 2. User selects what the other person speaks
    their_lang = st.selectbox("They will speak in:", ["English", "Tamil", "Kannada", "Hindi"])
    
    # 3. WhatsApp Number
    target_phone = st.text_input("Receiver's WhatsApp Number (e.g., 919876543210)")
    
    if st.button("Generate Call Link & Invite"):
        # We use query parameters so the receiver knows which languages are set
        app_url = "https://your-app-link.streamlit.app" # REPLACE THIS WITH YOUR REAL URL
        invite_msg = f"Join my translated voice call: {app_url}/?sender_lang={my_lang}&receiver_lang={their_lang}"
        encoded_msg = urllib.parse.quote(invite_msg)
        whatsapp_url = f"https://api.whatsapp.com/send?phone={target_phone}&text={encoded_msg}"
        
        # This creates a real clickable button for WhatsApp
        st.markdown(f'''
            <a href="{whatsapp_url}" target="_blank" style="text-decoration: none;">
                <div style="background-color: #25D366; color: white; padding: 15px; text-align: center; border-radius: 10px; font-weight: bold;">
                    Click Here to Send WhatsApp Invitation
                </div>
            </a>
            ''', unsafe_allow_html=True)
        
        # Save choices
        st.session_state.my_lang = my_lang
        st.session_state.their_lang = their_lang
        st.session_state.call_active = True

# --- 4. THE ACTIVE CALL INTERFACE ---
else:
    # Logic to check if user is the Sender or Receiver via URL
    # For now, we provide both buttons so either side can talk
    st.subheader(f"Call Active: {st.session_state.my_lang} ↔ {st.session_state.their_lang}")
    
    lmap = {"Tamil":"ta", "English":"en", "Kannada":"kn", "Hindi":"hi"}
    
    col1, col2 = st.columns(2)

    with col1:
        st.info(f"Speak {st.session_state.my_lang}")
        v1 = st.session_state.get('v1', 0)
        audio1 = mic_recorder(start_prompt="🎤 Start Talking", stop_prompt="⏹️ Stop", key=f"m1_{v1}")
        
        if audio1:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio1['bytes'])
                tmp_path = tmp.name
            
            try:
                # SPEED IMPROVEMENT: Use fp16=False if running on CPU (Streamlit Cloud)
                result = model.transcribe(tmp_path, language=lmap[st.session_state.my_lang], fp16=False)
                text = result['text'].strip()
                
                if text:
                    st.write(f"**Heard:** {text}")
                    trans = GoogleTranslator(source=lmap[st.session_state.my_lang], target=lmap[st.session_state.their_lang]).translate(text)
                    st.success(f"**Translated:** {trans}")
                    
                    fname = f"s1_{int(time.time())}.mp3"
                    gTTS(text=trans, lang=lmap[st.session_state.their_lang]).save(fname)
                    
                    # Duration check for full playback
                    duration = MP3(fname).info.length
                    play_audio(fname)
                    time.sleep(duration + 0.5) # Wait for audio to finish
                    
                    os.remove(fname)
                    st.session_state.v1 = v1 + 1
                    st.rerun()
            finally:
                if os.path.exists(tmp_path): os.remove(tmp_path)

    with col2:
        st.info(f"Speak {st.session_state.their_lang}")
        v2 = st.session_state.get('v2', 0)
        audio2 = mic_recorder(start_prompt="🎤 Start Talking", stop_prompt="⏹️ Stop", key=f"m2_{v2}")
        
        if audio2:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio2['bytes'])
                tmp_path = tmp.name
            
            try:
                result = model.transcribe(tmp_path, language=lmap[st.session_state.their_lang], fp16=False)
                text = result['text'].strip()
                
                if text:
                    st.write(f"**Heard:** {text}")
                    trans = GoogleTranslator(source=lmap[st.session_state.their_lang], target=lmap[st.session_state.my_lang]).translate(text)
                    st.success(f"**Translated:** {trans}")
                    
                    fname = f"s2_{int(time.time())}.mp3"
                    gTTS(text=trans, lang=lmap[st.session_state.my_lang]).save(fname)
                    
                    duration = MP3(fname).info.length
                    play_audio(fname)
                    time.sleep(duration + 0.5)
                    
                    os.remove(fname)
                    st.session_state.v2 = v2 + 1
                    st.rerun()
            finally:
                if os.path.exists(tmp_path): os.remove(tmp_path)

    if st.button("End Call"):
        st.session_state.call_active = False
        st.rerun()











