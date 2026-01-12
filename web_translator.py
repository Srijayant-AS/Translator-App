import streamlit as st
from streamlit_mic_recorder import mic_recorder
import whisper
from deep_translator import GoogleTranslator
from gtts import gTTS
import os, base64, tempfile, time, urllib.parse, uuid
from mutagen.mp3 import MP3
import streamlit.components.v1 as components

# --- 1. CLEAN UI (No Streamlit Branding) ---
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

# CASE A: SENDER SETUP
if not room_id:
    st.title("📞 Start a Translated Call")
    my_l = st.selectbox("I will speak in:", ["Tamil", "English", "Kannada", "Hindi"])
    phone = st.text_input("Receiver's WhatsApp (e.g., 919876543210)")

    if 'room_link' not in st.session_state:
        st.session_state.room_link = ""

    if st.button("Generate Secure Room"):
        new_room = str(uuid.uuid4())[:8]
        # This JS script grabs the URL and Room ID and copies to clipboard
        js_code = f"""
            <script>
            const url = window.location.origin + window.location.pathname + "?room={new_room}&slang={my_l}";
            navigator.clipboard.writeText(url);
            alert("Room Link Copied to Clipboard!");
            </script>
        """
        components.html(js_code, height=0)
        
        wa_msg = urllib.parse.quote(f"Join my private voice bridge. I have copied the link to my clipboard, I will paste it now.")
        wa_url = f"https://api.whatsapp.com/send?phone={phone}&text={wa_msg}"
        
        st.success("✅ Link Copied! Now open WhatsApp and paste it.")
        st.markdown(f'''
            <a href="{wa_url}" target="_blank" style="text-decoration:none;">
                <div style="background-color:#25D366;color:white;padding:15px;border-radius:10px;text-align:center;font-weight:bold;">
                    📲 Open WhatsApp to Paste & Send
                </div>
            </a>''', unsafe_allow_html=True)
        
        if st.button("Enter My Room"):
            st.query_params.update(room=new_room, slang=my_l, role="sender")
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
    aud = mic_recorder(start_prompt="Start Talking", stop_prompt="Stop", key=f"mic_{r_id}_{role}")

    if aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(aud['bytes'])
            tmp_path = tmp.name
        try:
            with st.spinner("Processing..."):
                result = model.transcribe(tmp_path, language=lmap[my_label], fp16=False, initial_prompt="Colloquial slang.")
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
                    time.sleep(1) # Final history delete
                    st.rerun()
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)

    if st.button("❌ End Call"):
        st.query_params.clear()
        st.rerun()












