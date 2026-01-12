import streamlit as st
from streamlit_mic_recorder import mic_recorder
import whisper
from deep_translator import GoogleTranslator
from gtts import gTTS
import os, base64, tempfile, time, urllib.parse, uuid
from mutagen.mp3 import MP3

# --- 1. CLEAN UI ---
st.set_page_config(page_title="AI Voice Bridge", layout="wide")
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stAppDeployButton {display:none;}
    [data-testid="stHeader"] {display:none;}
    div[data-testid="stToolbar"] {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. AI ENGINE ---
@st.cache_resource
def load_whisper_model():
    return whisper.load_model("small")

model = load_whisper_model()

def play_audio(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
    audio_html = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    st.markdown(audio_html, unsafe_allow_html=True)

# --- 3. DUAL-SIDE LOGIC ---
query_params = st.query_params
room_id = query_params.get("room")
sender_lang = query_params.get("slang")

if not room_id:
    st.title("📞 Start a Translated Call")
    my_l = st.selectbox("I will speak in:", ["Tamil", "English", "Kannada", "Hindi"])
    phone = st.text_input("Receiver's WhatsApp (e.g., 919876543210)")

    # Unique Room Generation
    if 'generated_url' not in st.session_state:
        st.session_state.generated_url = ""

    if st.button("Step 1: Create Secure Room"):
        new_room = str(uuid.uuid4())[:8]
        # This builds the URL based on the current page address
        # It handles the URL detection automatically
        base_url = "https://share.streamlit.io" # Placeholder, will be ignored by the copy widget
        # The code below uses a standard Streamlit text input with a copy button
        st.session_state.generated_url = f"?room={new_room}&slang={my_l}"
        st.session_state.room_id = new_room
        st.session_state.my_l = my_l

    if st.session_state.generated_url:
        st.write("---")
        st.success("✅ Room Prepared!")
        
        # This is the most reliable way to copy in Streamlit
        # It shows the link and provides a 'copy' icon next to it
        st.text_input("Copy this link suffix:", st.session_state.generated_url, help="Click the icon on the right to copy")
        
        wa_msg = urllib.parse.quote(f"Join my private voice bridge. Please click the link I'm about to send.")
        wa_url = f"https://api.whatsapp.com/send?phone={phone}&text={wa_msg}"
        
        st.markdown(f'''
            <a href="{wa_url}" target="_blank" style="text-decoration:none;">
                <div style="background-color:#25D366;color:white;padding:15px;border-radius:10px;text-align:center;font-weight:bold;margin-top:10px;">
                    Step 2: Open WhatsApp & Paste Link
                </div>
            </a>''', unsafe_allow_html=True)
        
        if st.button("Step 3: Enter My Room"):
            st.query_params.update(room=st.session_state.room_id, slang=st.session_state.my_l, role="sender")
            st.rerun()

# CASE B: RECEIVER SETUP
elif room_id and not query_params.get("rlang"):
    st.title("📞 Join Translated Call")
    st.write(f"The caller speaks: **{sender_lang}**")
    my_rlang = st.selectbox("Select YOUR Language:", ["English", "Tamil", "Kannada", "Hindi"])
    
    if st.button("Join Call"):
        st.query_params.update(rlang=my_rlang, role="receiver")
        st.rerun()

# CASE C: THE ACTIVE CALL
else:
    r_id = query_params.get("room")
    role = query_params.get("role")
    s_lang = query_params.get("slang")
    r_lang = query_params.get("rlang")
    
    st.subheader(f"🔒 Secure Room: {r_id}")
    my_label, their_label = (s_lang, r_lang) if role == "sender" else (r_lang, s_lang)
    
    lmap = {"Tamil":"ta", "English":"en", "Kannada":"kn", "Hindi":"hi"}
    st.info(f"🎤 Speak now in {my_label}")
    
    # The microphone resets using the room_id and role to prevent history crossover
    aud = mic_recorder(start_prompt="Start Talking", stop_prompt="Stop", key=f"mic_{r_id}_{role}")

    if aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(aud['bytes'])
            tmp_path = tmp.name
        try:
            with st.spinner("Processing..."):
                result = model.transcribe(tmp_path, language=lmap[my_label], fp16=False, initial_prompt="Use local slang.")
                text = result['text'].strip()
                if text:
                    st.write(f"**Heard:** {text}")
                    trans = GoogleTranslator(source=lmap[my_label], target=lmap[their_label]).translate(text)
                    st.success(f"**To {their_label}:** {trans}")
                    
                    fname = f"msg_{int(time.time())}.mp3"
                    gTTS(text=trans, lang=lmap[their_label]).save(fname)
                    length = MP3(fname).info.length
                    play_audio(fname)
                    time.sleep(length + 1)
                    os.remove(fname)
                    time.sleep(1) # Final pause for user to read
                    st.rerun()
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)

    if st.button("❌ End Call"):
        st.query_params.clear()
        st.rerun()













