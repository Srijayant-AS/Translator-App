import streamlit as st
from streamlit_mic_recorder import mic_recorder
import whisper
from deep_translator import GoogleTranslator
from gtts import gTTS
import os, base64, tempfile, time, urllib.parse, uuid
from supabase import create_client
from datetime import datetime, timedelta

# --- 1. CONFIGURATION ---
URL = "https://brcwrgmifldflevgukdt.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJyY3dyZ21pZmxkZmxldmd1a2R0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgzMTAxNDEsImV4cCI6MjA4Mzg4NjE0MX0.vX8RTdbUItPFENvxbN2S5m2axU8EgMspsAd5Pl6498w"

supabase = create_client(URL, KEY)

st.set_page_config(page_title="Live Voice Bridge", layout="wide")
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stAppDeployButton {display:none;} [data-testid="stHeader"] {display:none;}
    .partner-bubble { background-color: #e3f2fd; padding: 20px; border-radius: 15px; border-left: 8px solid #2196f3; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_whisper(): return whisper.load_model("tiny")
model = load_whisper()

def cleanup_db():
    limit = (datetime.now() - timedelta(minutes=30)).isoformat()
    try: supabase.table("call_messages").delete().lt("created_at", limit).execute()
    except: pass

# --- 2. LIVE INBOX FRAGMENT (The Auto-Refresh Magic) ---
@st.fragment(run_every=3) # Auto-refreshes this section every 3 seconds
def live_inbox(room_id, role, my_lang, lmap):
    other_role = "receiver" if role == "sender" else "sender"
    try:
        data = supabase.table("call_messages").select("*").eq("room_id", room_id).eq("sender_role", other_role).order("created_at", desc=True).limit(1).execute()
        
        if data.data:
            latest_msg = data.data[0]['message_text']
            st.markdown(f'<div class="partner-bubble"><b>Partner said:</b><br><h2>{latest_msg}</h2></div>', unsafe_allow_html=True)
            
            if st.button("🔊 READ OUT LOUD", key="play_btn"):
                fname = f"voice_{uuid.uuid4().hex}.mp3"
                gTTS(text=latest_msg, lang=lmap[my_lang]).save(fname)
                with open(fname, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
                time.sleep(1)
                os.remove(fname)
        else:
            st.info("⌛ Listening for partner's voice...")
    except Exception as e:
        st.error("Connection lost. Trying again...")

# --- 3. MAIN APP LOGIC ---
params = st.query_params
room_id = params.get("room")
role = params.get("role")
my_lang = params.get("ml")
their_lang = params.get("tl")
lmap = {"Tamil":"ta", "English":"en", "Kannada":"kn", "Hindi":"hi"}

if not room_id:
    st.title("📞 Live AI Intercom")
    cleanup_db()
    ml = st.selectbox("I speak:", ["Tamil", "English", "Kannada", "Hindi"])
    tl = st.selectbox("Partner speaks:", ["English", "Tamil", "Kannada", "Hindi"])
    phone = st.text_input("Partner's WhatsApp")
    
    if st.button("🚀 Open Channel"):
        rid = str(uuid.uuid4())[:8]
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        host = _get_websocket_headers().get("Host")
        link = f"https://{host}/?room={rid}&role=receiver&ml={tl}&tl={ml}"
        st.success("Channel Ready!")
        st.text_input("Copy Link:", link)
        wa_url = f"https://api.whatsapp.com/send?phone={phone}&text={urllib.parse.quote('Join call: ' + link)}"
        st.markdown(f'<a href="{wa_url}" target="_blank">📲 Send to WhatsApp</a>', unsafe_allow_html=True)
        if st.button("Enter Room"):
            st.query_params.update(room=rid, role="sender", ml=ml, tl=tl)
            st.rerun()
else:
    st.subheader(f"📡 Secure Channel: {room_id}")
    
    # Run the auto-refreshing inbox
    live_inbox(room_id, role, my_lang, lmap)
    
    st.divider()
    
    # Recording Section (Static - won't refresh while you are speaking)
    st.write(f"🎤 Record your response in **{my_lang}**")
    aud = mic_recorder(start_prompt="Start Speaking", stop_prompt="Send Translation", key="mic_static")

    if aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(aud['bytes'])
            tmp_path = tmp.name
        try:
            with st.spinner("🚀 Sending..."):
                res = model.transcribe(tmp_path, language=lmap[my_lang], fp16=False)
                trans = GoogleTranslator(source=lmap[my_lang], target=lmap[their_lang]).translate(res['text'])
                supabase.table("call_messages").insert({"room_id": room_id, "sender_role": role, "message_text": trans}).execute()
                st.success("Sent!")
                time.sleep(1)
                st.rerun()
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)

    if st.button("❌ End Session"):
        st.query_params.clear()
        st.rerun()













