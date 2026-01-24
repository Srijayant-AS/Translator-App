import streamlit as st
from streamlit_mic_recorder import mic_recorder
import whisper
from deep_translator import GoogleTranslator
from gtts import gTTS
import os, base64, tempfile, time, urllib.parse, uuid
from supabase import create_client

# --- 1. SUPABASE CONNECTION ---
URL = "https://brcwrgmifldflevgukdt.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJyY3dyZ21pZmxkZmxldmd1a2R0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgzMTAxNDEsImV4cCI6MjA4Mzg4NjE0MX0.vX8RTdbUItPFENvxbN2S5m2axU8EgMspsAd5Pl6498w"

@st.cache_resource
def get_supabase():
    return create_client(URL, KEY)

supabase = get_supabase()

# --- 2. MODELS & UI ---
st.set_page_config(page_title="Voice Bridge", layout="wide")
st.markdown("<style>header, footer, .stAppDeployButton, #GithubIcon, [data-testid='stHeader'] { visibility: hidden !important; }</style>", unsafe_allow_html=True)

@st.cache_resource
def load_whisper():
    return whisper.load_model("tiny", device="cpu")

model = load_whisper()

if "played_ids" not in st.session_state:
    st.session_state.played_ids = set()

def play_voice(msg_id, text, lang_code):
    """Plays audio once and marks as played"""
    if msg_id in st.session_state.played_ids:
        return
    st.session_state.played_ids.add(msg_id)
    
    f_path = f"v_{uuid.uuid4().hex}.mp3"
    try:
        gTTS(text=text, lang=lang_code).save(f_path)
        with open(f_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        # Safe delete
        try: supabase.table("call_messages").delete().eq("id", msg_id).execute()
        except: pass
        time.sleep(1)
        os.remove(f_path)
    except: pass

# --- 3. NAVIGATION (WhatsApp Flow Retained) ---
params = st.query_params
room_id = params.get("room")
role = params.get("role", "sender")
is_active = params.get("active") == "true"

if not room_id:
    st.title("📞 Stable Translator")
    my_lang = st.selectbox("I speak in:", ["Tamil", "English", "Kannada", "Hindi"])
    if st.button("🔗 CREATE LINK"):
        rid = str(uuid.uuid4())[:8]
        host = st.context.headers.get("host")
        link = f"https://{host}/?room={rid}&role=receiver"
        st.session_state.invite_link, st.session_state.temp_rid = link, rid
    if "invite_link" in st.session_state:
        wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote('Join call: ' + st.session_state.invite_link)}"
        st.markdown(f'<a href="{wa_url}" target="_blank"><div style="background-color:#25D366;color:white;padding:15px;border-radius:10px;text-align:center;font-weight:bold;">📲 WhatsApp Invite</div></a>', unsafe_allow_html=True)
        if st.button("✅ JOIN NOW"):
            st.query_params.update(room=st.session_state.temp_rid, role="sender", ml=my_lang, active="true")
            st.rerun()

elif room_id and not is_active:
    st.title("📩 Invitation")
    my_lang = st.selectbox("I speak in:", ["English", "Tamil", "Kannada", "Hindi"])
    if st.button("🚀 JOIN"):
        st.query_params.update(room=room_id, role="receiver", ml=my_lang, active="true")
        st.rerun()

else:
    # --- ACTIVE CALL ---
    lmap = {"Tamil":"ta", "English":"en", "Kannada":"kn", "Hindi":"hi"}
    my_lang = st.selectbox("My Language:", list(lmap.keys()), key="user_lang")
    
    # Push settings only once to save connection
    if "settings_pushed" not in st.session_state:
        try:
            supabase.table("call_messages").upsert({"room_id": room_id, "sender_role": f"{role}_settings", "message_text": my_lang}).execute()
            st.session_state.settings_pushed = True
        except: pass

    @st.fragment(run_every=3) # Slowed down to prevent ConnectError
    def inbox():
        other_role = "receiver" if role == "sender" else "sender"
        try:
            res = supabase.table("call_messages").select("*").eq("room_id", room_id).eq("sender_role", other_role).order("created_at", desc=True).limit(1).execute()
            if res.data:
                msg = res.data[0]
                if msg["id"] not in st.session_state.played_ids:
                    st.success(f"Partner: {msg['message_text']}")
                    play_voice(msg["id"], msg["message_text"], lmap[my_lang])
        except: pass

    inbox()
    st.divider()

    aud = mic_recorder(start_prompt="🎤 START SPEAKING", stop_prompt="⏹️ SEND", key="mic")
    if aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(aud['bytes']); tmp_path = tmp.name
        try:
            with st.spinner("🚀 Processing..."):
                # Meaning Fix: Direct Whisper Translate
                result = model.transcribe(tmp_path, language=lmap[my_lang], task="translate", fp16=False)
                eng_meaning = result['text'].strip()
                
                if eng_meaning:
                    # Get partner language only when sending
                    other_role = "receiver" if role == "sender" else "sender"
                    try:
                        p_set = supabase.table("call_messages").select("message_text").eq("room_id", room_id).eq("sender_role", f"{other_role}_settings").limit(1).execute()
                        target_lang = p_set.data[0]['message_text'] if (p_set and p_set.data) else "English"
                        
                        final_msg = GoogleTranslator(source='en', target=lmap[target_lang]).translate(eng_meaning)
                        supabase.table("call_messages").insert({"room_id": room_id, "sender_role": role, "message_text": final_msg}).execute()
                        
                        # Clear old history local memory so we only hear the NEW reply
                        st.session_state.played_ids.clear()
                        st.rerun()
                    except: st.error("Connection lost. Please try speaking again.")
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)


































