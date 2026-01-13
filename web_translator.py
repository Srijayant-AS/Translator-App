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

# --- 2. CLEAN UI (STRICT HIDDEN ICONS) ---
st.set_page_config(page_title="Voice Bridge", layout="wide")
st.markdown("""
    <style>
    header, footer, .stAppDeployButton, #GithubIcon, [data-testid="stHeader"] { visibility: hidden !important; height: 0px !important; }
    .partner-msg { background-color: #e8f5e9; padding: 20px; border-radius: 15px; border-left: 8px solid #4caf50; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    .stSelectbox label { font-weight: bold; font-size: 1.1rem; }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_whisper(): return whisper.load_model("tiny")
model = load_whisper()

def play_audio_auto(text, lang_code):
    """Generates and injects an autoplaying audio tag"""
    f_path = f"temp_{uuid.uuid4().hex}.mp3"
    gTTS(text=text, lang=lang_code).save(f_path)
    with open(f_path, "rb") as audio_file:
        b64 = base64.b64encode(audio_file.read()).decode()
    st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
    os.remove(f_path)

# --- 3. MAIN LOGIC ---
params = st.query_params
room_id = params.get("room")
role = params.get("role", "sender")

if not room_id:
    st.title("📞 Instant Translated Call")
    my_lang = st.selectbox("I speak in:", ["Tamil", "English", "Kannada", "Hindi"])
    
    if st.button("🚀 CREATE ROOM & INVITE"):
        rid = str(uuid.uuid4())[:8]
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        host = _get_websocket_headers().get("Host")
        
        invite_link = f"https://{host}/?room={rid}&role=receiver"
        wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote('Join our translated call: ' + invite_link)}"
        
        st.success("✅ Room Created!")
        st.code(invite_link)
        st.markdown(f'<a href="{wa_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:15px;border-radius:10px;text-align:center;font-weight:bold;margin-bottom:15px;">📲 Share to WhatsApp</div></a>', unsafe_allow_html=True)
        
        if st.button("Step 2: Enter Room Now"):
            st.query_params.update(room=rid, role="sender", ml=my_lang)
            st.rerun()

else:
    st.subheader(f"📡 Secure Call ID: {room_id}")
    my_lang = st.selectbox("My Language:", ["Tamil", "English", "Kannada", "Hindi"], key="user_lang")
    lmap = {"Tamil":"ta", "English":"en", "Kannada":"kn", "Hindi":"hi"}

    # Handshake Settings
    supabase.table("call_messages").upsert({"room_id": room_id, "sender_role": f"{role}_settings", "message_text": my_lang}).execute()

    # --- AUTO-REFRESH INBOX FRAGMENT ---
    @st.fragment(run_every=3)
    def auto_inbox():
        other_role = "receiver" if role == "sender" else "sender"
        try:
            res = supabase.table("call_messages").select("*").eq("room_id", room_id).eq("sender_role", other_role).order("created_at", desc=True).limit(1).execute()
            
            if res.data:
                msg_data = res.data[0]
                msg_id = msg_data['id']
                msg_text = msg_data['message_text']

                # Display the message
                st.markdown(f'<div class="partner-msg"><b>Partner:</b><br><h3>{msg_text}</h3></div>', unsafe_allow_html=True)

                # AUTOPLAY LOGIC: Only play if this is a NEW message ID
                if "last_played_id" not in st.session_state or st.session_state.last_played_id != msg_id:
                    play_audio_auto(msg_text, lmap[my_lang])
                    st.session_state.last_played_id = msg_id
            else:
                st.info("⌛ Listening for partner's voice...")

            # Fetch partner's language for the translation engine
            p_data = supabase.table("call_messages").select("message_text").eq("room_id", room_id).eq("sender_role", f"{other_role}_settings").limit(1).execute()
            return p_data.data[0]['message_text'] if p_data.data else "English"
        except: return "English"

    target_lang = auto_inbox()
    st.divider()

    # --- VOICE CAPTURE ---
    st.write(f"🎤 Record your response in **{my_lang}**")
    aud = mic_recorder(start_prompt="START SPEAKING", stop_prompt="STOP & SEND", key="call_mic")

    if aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(aud['bytes'])
            tmp_path = tmp.name
        try:
            with st.spinner("🚀 Translating..."):
                res = model.transcribe(tmp_path, language=lmap[my_lang], fp16=False)
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















