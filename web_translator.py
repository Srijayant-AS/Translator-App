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

# --- 2. CLEAN UI (NO ICONS) ---
st.set_page_config(page_title="Voice Bridge", layout="wide")
st.markdown("""
    <style>
    header, footer, .stAppDeployButton, #GithubIcon, [data-testid="stHeader"] { visibility: hidden !important; display: none !important; }
    .partner-msg { background-color: #f1f8e9; padding: 25px; border-radius: 15px; border-left: 10px solid #4caf50; margin: 15px 0; box-shadow: 0px 4px 6px rgba(0,0,0,0.05); }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_whisper():
    return whisper.load_model("base", device="cpu")

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

# --- 3. NAVIGATION ---
params = st.query_params
room_id = params.get("room")
role = params.get("role", "sender")
is_active = params.get("active") == "true"

# --- STEP 1: SENDER SETUP ---
if not room_id:
    st.title("📞 Start Private Discussion")
    my_lang = st.selectbox("I speak in:", ["Tamil", "English", "Kannada", "Hindi"])
    
    if st.button("🔗 GENERATE UNIQUE LINK"):
        rid = str(uuid.uuid4())[:8]
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        host = _get_websocket_headers().get("Host")
        invite_link = f"https://{host}/?room={rid}&role=receiver"
        st.session_state.invite_link = invite_link
        st.session_state.temp_rid = rid

    if "invite_link" in st.session_state:
        st.info(f"Link Generated: {st.session_state.invite_link}")
        wa_text = f"Join my private call: {st.session_state.invite_link}"
        wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(wa_text)}"
        st.markdown(f'<a href="{wa_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:15px;border-radius:10px;text-align:center;font-weight:bold;">📲 Send Invite via WhatsApp</div></a>', unsafe_allow_html=True)
        st.write("")
        if st.button("✅ JOIN ROOM NOW"):
            st.query_params.update(room=st.session_state.temp_rid, role="sender", ml=my_lang, active="true")
            st.rerun()

# --- STEP 2: RECEIVER SETUP ---
elif room_id and not is_active:
    st.title("📩 You are Invited")
    my_lang = st.selectbox("I speak in:", ["English", "Tamil", "Kannada", "Hindi"])
    if st.button("🚀 JOIN DISCUSSION"):
        st.query_params.update(room=room_id, role="receiver", ml=my_lang, active="true")
        st.rerun()

# --- STEP 3: THE ACTIVE CHAT ---
else:
    st.subheader(f"📡 Secure Call ID: {room_id}")
    my_lang = st.selectbox("My Language:", ["Tamil", "English", "Kannada", "Hindi"], key="user_lang")
    lmap = {"Tamil":"ta", "English":"en", "Kannada":"kn", "Hindi":"hi"}

    # Register my language so the partner's app knows what to translate TO
    supabase.table("call_messages").upsert({"room_id": room_id, "sender_role": f"{role}_settings", "message_text": my_lang}).execute()

    @st.fragment(run_every=2) # Faster check for a more "live" feel
    def auto_inbox():
        other_role = "receiver" if role == "sender" else "sender"
        try:
            # Fetch ONLY the single most recent message from the partner
            res = supabase.table("call_messages").select("*").eq("room_id", room_id).eq("sender_role", other_role).order("created_at", desc=True).limit(1).execute()
            
            # Fetch partner's current language choice
            p_settings = supabase.table("call_messages").select("message_text").eq("room_id", room_id).eq("sender_role", f"{other_role}_settings").limit(1).execute()
            p_lang = p_settings.data[0]['message_text'] if p_settings.data else "English"

            if res.data:
                msg_data = res.data[0]
                mid, mtext = msg_data['id'], msg_data['message_text']
                
                # Show the most recent message only
                st.markdown(f'<div class="partner-msg"><b>Partner ({p_lang}):</b><br><h3>{mtext}</h3></div>', unsafe_allow_html=True)
                
                # Automatic Audio: Trigger only if this ID hasn't been played yet
                if "last_played_id" not in st.session_state or st.session_state.last_played_id != mid:
                    play_audio_auto(mtext, lmap[my_lang])
                    st.session_state.last_played_id = mid
            else:
                st.info("⌛ Waiting for partner's response...")
            return p_lang
        except Exception as e:
            return "English"

    target_lang = auto_inbox()
    st.divider()

    st.write(f"🎤 Speak in **{my_lang}**:")
    aud = mic_recorder(start_prompt="START RECORDING", stop_prompt="STOP & SEND", key="call_mic")

    if aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(aud['bytes'])
            tmp_path = tmp.name
        try:
            with st.spinner("🚀 Translating..."):
                # Accuracy Fix (Base Model + CPU Float32)
                res = model.transcribe(tmp_path, fp16=False)
                text = res['text'].strip()
                if text:
                    # Translate to the target language currently set by the partner
                    trans = GoogleTranslator(source=lmap[my_lang], target=lmap[target_lang]).translate(text)
                    # Send to DB
                    supabase.table("call_messages").insert({"room_id": room_id, "sender_role": role, "message_text": trans}).execute()
                    st.success("Sent!")
                    # Brief pause so the user sees the "Sent" status before refresh
                    time.sleep(0.5)
                    st.rerun()
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)

    if st.button("❌ End Session"):
        st.query_params.clear()
        st.rerun()


















