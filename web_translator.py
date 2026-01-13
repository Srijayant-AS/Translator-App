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

# --- 2. HIDE ALL TOP-RIGHT ICONS (GitHub, Deploy, Menu) ---
st.set_page_config(page_title="Voice Bridge", layout="wide")
st.markdown("""
    <style>
    /* Hide the top header entirely */
    header[data-testid="stHeader"] { visibility: hidden; height: 0px; }
    /* Hide the GitHub icon and Deploy button specifically */
    .stAppDeployButton, #GithubIcon, .stActionButton { display: none !important; }
    /* Hide the footer */
    footer { visibility: hidden; }
    /* Clean up the padding */
    .block-container { padding-top: 1rem; }
    .partner-msg { background-color: #f1f8e9; padding: 15px; border-radius: 12px; border-left: 8px solid #4caf50; }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_whisper(): return whisper.load_model("tiny")
model = load_whisper()

# --- 3. LOGIC ---
params = st.query_params
room_id = params.get("room")
role = params.get("role", "sender")

# --- SCREEN 1: THE ROOM CREATOR (SETUP) ---
if not room_id:
    st.title("📞 Create Voice Discussion")
    my_lang = st.selectbox("I speak:", ["Tamil", "English", "Kannada", "Hindi"])
    
    if st.button("🚀 GENERATE WHATSAPP INVITE"):
        rid = str(uuid.uuid4())[:8]
        # Get the actual URL of your deployed app
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        host = _get_websocket_headers().get("Host")
        
        # Link for the partner
        invite_link = f"https://{host}/?room={rid}&role=receiver"
        
        # WhatsApp Share Link
        wa_text = f"Join our private translated call here: {invite_link}"
        wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(wa_text)}"
        
        st.success("Invite Generated! Click the button below to send it.")
        st.markdown(f'''
            <a href="{wa_url}" target="_blank" style="text-decoration:none;">
                <div style="background-color:#25D366;color:white;padding:15px;border-radius:10px;text-align:center;font-weight:bold;font-size:18px;">
                    📲 Open WhatsApp to Invite Partner
                </div>
            </a>''', unsafe_allow_html=True)
        
        if st.button("Enter Chat Room"):
            st.query_params.update(room=rid, role="sender", ml=my_lang)
            st.rerun()

# --- SCREEN 2: THE CHAT ROOM (ACTIVE) ---
else:
    st.subheader(f"📡 Secure Call ID: {room_id}")
    my_lang = st.selectbox("My Language:", ["Tamil", "English", "Kannada", "Hindi"], key="user_lang")
    
    # Handshake: Save my language choice to DB
    supabase.table("call_messages").upsert({
        "room_id": room_id, "sender_role": f"{role}_settings", "message_text": my_lang
    }).execute()

    # Fragment for real-time inbox
    @st.fragment(run_every=3)
    def inbox_fragment():
        other_role = "receiver" if role == "sender" else "sender"
        data = supabase.table("call_messages").select("*").eq("room_id", room_id).order("created_at", desc=True).execute()
        
        partner_lang = "English"
        latest_msg = None
        for row in data.data:
            if row['sender_role'] == f"{other_role}_settings": partner_lang = row['message_text']
            if row['sender_role'] == other_role and not latest_msg: latest_msg = row['message_text']

        if latest_msg:
            st.markdown(f'<div class="partner-msg"><b>Partner ({partner_lang}):</b><br><h3>{latest_msg}</h3></div>', unsafe_allow_html=True)
            if st.button("🔊 READ MESSAGE"):
                lmap = {"Tamil":"ta", "English":"en", "Kannada":"kn", "Hindi":"hi"}
                fname = f"voice_{uuid.uuid4().hex}.mp3"
                gTTS(text=latest_msg, lang=lmap[my_lang]).save(fname)
                with open(fname, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
                os.remove(fname)
        return partner_lang

    partner_lang = inbox_fragment()
    st.divider()

    # Record and Send
    aud = mic_recorder(start_prompt="🎤 Speak", stop_prompt="⏹️ Send to Partner", key="mic")
    if aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(aud['bytes']); tmp_path = tmp.name
        try:
            with st.spinner("🚀 Translating..."):
                lmap = {"Tamil":"ta", "English":"en", "Kannada":"kn", "Hindi":"hi"}
                res = model.transcribe(tmp_path, language=lmap[my_lang], fp16=False)
                trans = GoogleTranslator(source=lmap[my_lang], target=lmap[partner_lang]).translate(res['text'])
                supabase.table("call_messages").insert({
                    "room_id": room_id, "sender_role": role, "message_text": trans
                }).execute()
                st.rerun()
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)

    if st.button("❌ Close Discussion"):
        st.query_params.clear()
        st.rerun()














