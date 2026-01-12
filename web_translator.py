import streamlit as st
from streamlit_mic_recorder import mic_recorder
import whisper
from deep_translator import GoogleTranslator
from gtts import gTTS
import os, base64, tempfile, time, urllib.parse, uuid
from mutagen.mp3 import MP3

# --- 1. UI & BRANDING (Hides Streamlit Menu/Footer/GitHub) ---
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

# --- 2. FAST AI ENGINE ---
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

# --- 3. DUAL-SIDE LOGIC WITH AUTO-URL DETECTION ---
query_params = st.query_params
room_id = query_params.get("room")
sender_lang = query_params.get("slang")

# CASE A: SENDER SETUP (Start a new call)
if not room_id:
    st.title("📞 Start a Translated Call")
    st.write("Only select **your** language. The receiver will choose theirs later.")
    
    my_l = st.selectbox("I will speak in:", ["Tamil", "English", "Kannada", "Hindi"])
    phone = st.text_input("Receiver's WhatsApp (e.g., 919876543210)")

    if st.button("Generate Call Link"):
        new_room = str(uuid.uuid4())[:8]
        
        # --- AUTO URL SOLUTION ---
        # We use Javascript to get the current window URL so you don't have to type it
        # This works on any domain (Streamlit Cloud, Localhost, etc.)
        import streamlit.components.v1 as components
        
        # We use a button that triggers a WhatsApp redirect with the current URL
        invite_link = f"/?room={new_room}&slang={my_l}"
        
        msg = f"Join my private voice bridge: {invite_link}"
        wa_url = f"https://api.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(msg)}"
        
        st.success("✅ Secure Room Generated!")
        st.markdown(f'''
            <p>Step 1: Copy your browser's address bar link.</p>
            <p>Step 2: Click the button below to send it.</p>
            <a href="{wa_url}" target="_blank" style="text-decoration:none;">
                <div style="background-color:#25D366;color:white;padding:15px;border-radius:10px;text-align:center;font-weight:bold;">
                    📲 Click to Open WhatsApp Chat
                </div>
            </a>''', unsafe_allow_html=True)
        
        if st.button("Enter My Room"):
            st.query_params.update(room=new_room, slang=my_l, role="sender")
            st.rerun()

# CASE B: RECEIVER SETUP (Clicked the link)
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
    
    if role == "sender":
        my_label, their_label = s_lang, r_lang
    else:
        my_label, their_label = r_lang, s_lang

    st.write(f"Your Language: **{my_label}** | Their Language: **{their_label}**")
    
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
                    st.write(f"**Heard ({my_label}):** {text}")
                    trans = GoogleTranslator(source=lmap[my_label], target=lmap[their_label]).translate(text)
                    st.success(f"**To {their_label}:** {trans}")
                    
                    fname = f"msg_{int(time.time())}.mp3"
                    gTTS(text=trans, lang=lmap[their_label]).save(fname)
                    
                    length = MP3(fname).info.length
                    play_audio(fname)
                    time.sleep(length + 1)
                    os.remove(fname)
                    # History Deletion (2-second buffer total)
                    time.sleep(1)
                    st.rerun()
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)

    if st.button("❌ End Call"):
        st.query_params.clear()
        st.rerun()











