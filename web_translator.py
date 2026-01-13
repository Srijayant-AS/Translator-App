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

st.set_page_config(page_title="Live AI Intercom", layout="wide")

@st.cache_resource
def load_whisper(): return whisper.load_model("tiny")
model = load_whisper()

def play_audio(text, lang_code):
    fname = f"voice_{uuid.uuid4().hex}.mp3"
    gTTS(text=text, lang=lang_code).save(fname)
    with open(fname, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
    os.remove(fname)

# --- 2. DYNAMIC LANGUAGE SYNC ---
@st.fragment(run_every=3)
def live_chat_room(room_id, my_role, my_lang_name):
    lmap = {"Tamil":"ta", "English":"en", "Kannada":"kn", "Hindi":"hi"}
    
    # Update my language in the DB so partner knows what to send
    supabase.table("call_messages").upsert({
        "room_id": room_id, "sender_role": f"{my_role}_settings", "message_text": my_lang_name
    }).execute()

    # Get Partner's Language & Latest Message
    other_role = "receiver" if my_role == "sender" else "sender"
    data = supabase.table("call_messages").select("*").eq("room_id", room_id).order("created_at", desc=True).execute()
    
    partner_lang = "English" # Default
    latest_msg = None

    for row in data.data:
        if row['sender_role'] == f"{other_role}_settings":
            partner_lang = row['message_text']
        if row['sender_role'] == other_role and not latest_msg:
            latest_msg = row['message_text']

    if latest_msg:
        st.markdown(f'<div style="background:#e3f2fd;padding:20px;border-radius:15px;"><b>Partner ({partner_lang}):</b><br><h2>{latest_msg}</h2></div>', unsafe_allow_html=True)
        if st.button("🔊 PLAY"): play_audio(latest_msg, lmap[my_lang_name])
    else:
        st.info(f"Waiting for partner... (Your lang: {my_lang_name})")
    
    return partner_lang

# --- 3. MAIN APP ---
params = st.query_params
room_id = params.get("room")
role = params.get("role", "sender")

if not room_id:
    st.title("📞 Start New Call")
    my_lang = st.selectbox("I speak:", ["Tamil", "English", "Kannada", "Hindi"])
    if st.button("🚀 Create Channel"):
        rid = str(uuid.uuid4())[:8]
        host = st.context.headers.get("Host")
        link = f"https://{host}/?room={rid}&role=receiver"
        st.success("Send this link to your partner:")
        st.code(link)
        st.query_params.update(room=rid, role="sender", ml=my_lang)
        st.rerun()
else:
    my_lang = st.selectbox("My Language:", ["Tamil", "English", "Kannada", "Hindi"], key="lang_sel")
    partner_lang = live_chat_room(room_id, role, my_lang)
    
    st.divider()
    aud = mic_recorder(start_prompt="🎤 Speak", stop_prompt="⏹️ Send", key="mic")
    
    if aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(aud['bytes']); tmp_path = tmp.name
        try:
            lmap = {"Tamil":"ta", "English":"en", "Kannada":"kn", "Hindi":"hi"}
            res = model.transcribe(tmp_path, language=lmap[my_lang], fp16=False)
            trans = GoogleTranslator(source=lmap[my_lang], target=lmap[partner_lang]).translate(res['text'])
            supabase.table("call_messages").insert({"room_id": room_id, "sender_role": role, "message_text": trans}).execute()
            st.rerun()
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)














