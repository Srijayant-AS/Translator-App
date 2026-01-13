import streamlit as st
from streamlit_mic_recorder import mic_recorder
import whisper
from deep_translator import GoogleTranslator
from gtts import gTTS
import os, base64, tempfile, time, urllib.parse, uuid
from supabase import create_client

# --- 1. SUPABASE CONFIG ---
URL = "https://brcwrgmifldflevgukdt.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJyY3dyZ21pZmxkZmxldmd1a2R0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgzMTAxNDEsImV4cCI6MjA4Mzg4NjE0MX0.vX8RTdbUItPFENvxbN2S5m2axU8EgMspsAd5Pl6498w"
supabase = create_client(URL, KEY)

# --- 2. PROFESSIONAL CLEAN UI ---
st.set_page_config(page_title="Voice Bridge", layout="wide")
st.markdown("""
    <style>
    header, footer, .stAppDeployButton, #GithubIcon, [data-testid="stHeader"] { visibility: hidden !important; display: none !important; }
    .partner-msg { background-color: #e8f5e9; padding: 20px; border-radius: 15px; border-left: 8px solid #4caf50; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_whisper():
    # Loading onto CPU specifically to avoid the Torch 3.13 error
    return whisper.load_model("tiny", device="cpu")

model = load_whisper()

def play_audio_auto(text, lang_code):
    f_path = f"v_{uuid.uuid4().hex}.mp3"
    try:
        gTTS(text=text, lang=lang_code).save(f_path)
        with open(f_path, "rb") as audio_file:
            b64 = base64.b64encode(audio_file.read()).decode()
        st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        time.sleep(1)
        os.remove(f_path)
    except: pass

# --- 3. MAIN NAVIGATION ---
params = st.query_params
room_id = params.get("room")
role = params.get("role", "sender")

# --- SCREEN 1: ROOM CREATION ---
if not room_id:
    st.title("📞 Instant Translated Call")
    my_lang = st.selectbox("I speak in:", ["Tamil", "English", "Kannada", "Hindi"])
    
    if st.button("🚀 CREATE ROOM & ENTER"):
        rid = str(uuid.uuid4())[:8]
        # Get the actual host URL
        try:
            from streamlit.web.server.websocket_headers import _get_websocket_headers
            host = _get_websocket_headers().get("Host")
        except:
            host = "localhost" # Fallback
            
        invite_link = f"https://{host}/?room={rid}&role=receiver"
        wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote('Join our call: ' + invite_link)}"
        
        # We save the room details and REDIRECT immediately
        st.query_params.update(room=rid, role="sender", ml=my_lang)
        
        # Display the WhatsApp link before the rerun happens
        st.success("✅ Room Created!")
        st.markdown(f'<a href="{wa_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:15px;border-radius:10px;text-align:center;font-weight:bold;">📲 Send Link via WhatsApp</div></a>', unsafe_allow_html=True)
        time.sleep(2)
        st.rerun()

# --- SCREEN 2: ACTIVE ROOM ---
else:
    st.subheader(f"📡 Secure Call ID: {room_id}")
    my_lang = st.selectbox("My Language:", ["Tamil", "English", "Kannada", "Hindi"], key="user_lang")
    lmap = {"Tamil":"ta", "English":"en", "Kannada":"kn", "Hindi":"hi"}

    # Sync My Settings to DB
    supabase.table("call_messages").upsert({"room_id": room_id, "sender_role": f"{role}_settings", "message_text": my_lang}).execute()

    # --- AUTO-REFRESH INBOX ---
    @st.fragment(run_every=3)
    def auto_inbox():
        other_role = "receiver" if role == "sender" else "sender"
        try:
            res = supabase.table("call_messages").select("*").eq("room_id", room_id).eq("sender_role", other_role).order("created_at", desc=True).limit(1).execute()
            
            p_lang = "English"
            p_settings = supabase.table("call_messages").select("message_text").eq("room_id", room_id).eq("sender_role", f"{other_role}_settings").limit(1).execute()
            if p_settings.data: p_lang = p_settings.data[0]['message_text']

            if res.data:
                msg_data = res.data[0]
                mid, mtext = msg_data['id'], msg_data['message_text']
                st.markdown(f'<div class="partner-msg"><b>Partner ({p_lang}):</b><br><h3>{mtext}</h3></div>', unsafe_allow_html=True)

                if "last_id" not in st.session_state or st.session_state.last_id != mid:
                    play_audio_auto(mtext, lmap[my_lang])
                    st.session_state.last_id = mid
            else:
                st.info("⌛ Waiting for partner...")
            return p_lang
        except: return "English"

    target_lang = auto_inbox()
    st.divider()

    # --- VOICE CAPTURE ---
    st.write(f"Speak in **{my_lang}**:")
    aud = mic_recorder(start_prompt="🎤 START", stop_prompt="⏹️ SEND", key="call_mic")

    if aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(aud['bytes'])
            tmp_path = tmp.name
        try:
            with st.spinner("🚀 Translating..."):
                # Using the transcription with CPU-safe settings
                res = model.transcribe(tmp_path, fp16=False)
                text = res['text'].strip()
                if text:
                    trans = GoogleTranslator(source=lmap[my_lang], target=lmap[target_lang]).translate(text)
                    supabase.table("call_messages").insert({"room_id": room_id, "sender_role": role, "message_text": trans}).execute()
                    st.rerun()
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)

    if st.button("❌ Close Discussion"):
        st.query_params.clear()
        st.rerun()
















