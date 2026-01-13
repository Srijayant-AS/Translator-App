import streamlit as st
from streamlit_mic_recorder import mic_recorder
import whisper
from deep_translator import GoogleTranslator
from gtts import gTTS
import os, base64, tempfile, time, urllib.parse, uuid
import numpy as np
import librosa
from supabase import create_client
import soundfile as sf

# --- 1. SUPABASE CONFIG ---
URL = "https://brcwrgmifldflevgukdt.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJyY3dyZ21pZmxkZmxldmd1a2R0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgzMTAxNDEsImV4cCI6MjA4Mzg4NjE0MX0.vX8RTdbUItPFENvxbN2S5m2axU8EgMspsAd5Pl6498w"
supabase = create_client(URL, KEY)

# --- 2. CLEAN UI ---
st.set_page_config(page_title="Voice Bridge", layout="wide")
st.markdown("<style>header, footer, .stAppDeployButton, #GithubIcon, [data-testid='stHeader'] { visibility: hidden !important; }</style>", unsafe_allow_html=True)

@st.cache_resource
def load_whisper():
    # 'base' model is more stable for long sentences and noise-handling
    return whisper.load_model("base", device="cpu")

model = load_whisper()

if "played_ids" not in st.session_state:
    st.session_state.played_ids = set()

def reduce_noise(file_path):
    """Simple spectral subtraction to reduce background noise"""
    y, sr = librosa.load(file_path, sr=None)
    # Estimate noise from the first 0.2 seconds
    noise_part = y[:int(sr*0.2)] if len(y) > int(sr*0.2) else y
    noise_val = np.mean(librosa.feature.melspectrogram(y=noise_part, sr=sr))
    # Apply soft gate
    y_clean = np.where(np.abs(y) < noise_val, 0, y)
    clean_path = file_path.replace(".wav", "_clean.wav")
    sf.write(clean_path, y_clean, sr)
    return clean_path

def play_voice(msg_id, text, lang_code):
    if msg_id in st.session_state.played_ids: return
    st.session_state.played_ids.add(msg_id)
    f_path = f"v_{uuid.uuid4().hex}.mp3"
    try:
        gTTS(text=text, lang=lang_code).save(f_path)
        with open(f_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        supabase.table("call_messages").delete().eq("id", msg_id).execute()
        time.sleep(1)
        os.remove(f_path)
    except: pass

# --- 3. NAVIGATION (WhatsApp/Join Flow Retained) ---
params = st.query_params
room_id = params.get("room"); role = params.get("role", "sender"); is_active = params.get("active") == "true"

if not room_id:
    st.title("📞 Noise-Free Translator")
    my_lang = st.selectbox("I speak in:", ["Tamil", "English", "Kannada", "Hindi"])
    if st.button("🔗 CREATE UNIQUE LINK"):
        rid = str(uuid.uuid4())[:8]
        host = st.context.headers.get("host")
        link = f"https://{host}/?room={rid}&role=receiver"
        st.session_state.invite_link, st.session_state.temp_rid = link, rid
    if "invite_link" in st.session_state:
        wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote('Join call: ' + st.session_state.invite_link)}"
        st.markdown(f'<a href="{wa_url}" target="_blank"><div style="background-color:#25D366;color:white;padding:15px;border-radius:10px;text-align:center;font-weight:bold;">📲 WhatsApp Invite</div></a>', unsafe_allow_html=True)
        if st.button("✅ JOIN ROOM NOW"):
            st.query_params.update(room=st.session_state.temp_rid, role="sender", ml=my_lang, active="true")
            st.rerun()
elif room_id and not is_active:
    st.title("📩 Invited to Call")
    my_lang = st.selectbox("I speak in:", ["English", "Tamil", "Kannada", "Hindi"])
    if st.button("🚀 JOIN NOW"):
        st.query_params.update(room=room_id, role="receiver", ml=my_lang, active="true")
        st.rerun()
else:
    # --- ACTIVE CALL ---
    lmap = {"Tamil":"ta", "English":"en", "Kannada":"kn", "Hindi":"hi"}
    my_lang = st.selectbox("My Language:", list(lmap.keys()), key="user_lang")
    supabase.table("call_messages").upsert({"room_id": room_id, "sender_role": f"{role}_settings", "message_text": my_lang}).execute()

    @st.fragment(run_every=2)
    def inbox_manager():
        other_role = "receiver" if role == "sender" else "sender"
        try:
            res = supabase.table("call_messages").select("*").eq("room_id", room_id).eq("sender_role", other_role).order("created_at", desc=True).limit(1).execute()
            if res.data:
                msg = res.data[0]
                if msg["id"] not in st.session_state.played_ids:
                    st.markdown(f'<div style="background:#f1f8e9;padding:20px;border-radius:15px;border-left:8px solid #4caf50;"><h3>{msg["message_text"]}</h3></div>', unsafe_allow_html=True)
                    play_voice(msg["id"], msg["message_text"], lmap[my_lang])
        except: pass

    inbox_manager()
    st.divider()

    aud = mic_recorder(start_prompt="🎤 START SPEAKING", stop_prompt="⏹️ SEND", key="mic")
    if aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(aud['bytes']); tmp_path = tmp.name
        try:
            with st.spinner("✨ Cleaning Audio & Translating..."):
                # 1. Noise Cancellation
                clean_path = reduce_noise(tmp_path)
                # 2. Transcription (Avoids crash by using base model + transcribe)
                result = model.transcribe(clean_path, language=lmap[my_lang], fp16=False)
                transcribed_text = result['text'].strip()
                
                if transcribed_text:
                    other_role = "receiver" if role == "sender" else "sender"
                    p_set = supabase.table("call_messages").select("message_text").eq("room_id", room_id).eq("sender_role", f"{other_role}_settings").limit(1).execute()
                    target_lang_name = p_set.data[0]['message_text'] if p_set.data else "English"
                    # 3. Meaning Translation
                    final_msg = GoogleTranslator(source='auto', target=lmap[target_lang_name]).translate(transcribed_text)
                    supabase.table("call_messages").insert({"room_id": room_id, "sender_role": role, "message_text": final_msg}).execute()
                    st.rerun()
        finally:
            for p in [tmp_path, clean_path]:
                if os.path.exists(p): os.remove(p)

























