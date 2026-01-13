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

# --- 2. CLEAN UI ---
st.set_page_config(page_title="Voice Bridge", layout="wide")
st.markdown("<style>header, footer, .stAppDeployButton, #GithubIcon, [data-testid='stHeader'] { visibility: hidden !important; height: 0px !important; }</style>", unsafe_allow_html=True)

@st.cache_resource
def load_whisper():
    return whisper.load_model("tiny", device="cpu")

model = load_whisper()

# Initialize the "Already Played" blacklist
if "played_ids" not in st.session_state:
    st.session_state.played_ids = set()

def play_voice(msg_id, text, lang_code):
    """Plays audio once and marks as played locally and in DB"""
    if msg_id in st.session_state.played_ids:
        return
    
    f_path = f"v_{uuid.uuid4().hex}.mp3"
    try:
        # Generate audio for the whole text (handles long sentences)
        tts = gTTS(text=text, lang=lang_code)
        tts.save(f_path)
        
        with open(f_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        
        # Autoplay injection
        st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        
        # Mark as played locally to stop loops
        st.session_state.played_ids.add(msg_id)
        
        # Delete from Supabase so history stays clean
        supabase.table("call_messages").delete().eq("id", msg_id).execute()
        
        time.sleep(1)
        os.remove(f_path)
    except:
        pass

# --- 3. NAVIGATION (WhatsApp & Join Buttons) ---
params = st.query_params
room_id = params.get("room")
role = params.get("role", "sender")
is_active = params.get("active") == "true"

if not room_id:
    st.title("📞 Private Voice Translator")
    my_lang = st.selectbox("I speak in:", ["Tamil", "English", "Kannada", "Hindi"])
    if st.button("🔗 CREATE UNIQUE LINK"):
        rid = str(uuid.uuid4())[:8]
        host = st.context.headers.get("host")
        link = f"https://{host}/?room={rid}&role=receiver"
        st.session_state.invite_link, st.session_state.temp_rid = link, rid
    
    if "invite_link" in st.session_state:
        st.info(f"Room Link: {st.session_state.invite_link}")
        wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote('Join my translated call: ' + st.session_state.invite_link)}"
        st.markdown(f'<a href="{wa_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:15px;border-radius:10px;text-align:center;font-weight:bold;">📲 Send via WhatsApp</div></a>', unsafe_allow_html=True)
        if st.button("✅ JOIN ROOM NOW"):
            st.query_params.update(room=st.session_state.temp_rid, role="sender", ml=my_lang, active="true")
            st.rerun()

elif room_id and not is_active:
    st.title("📩 Call Invitation")
    my_lang = st.selectbox("I speak in:", ["English", "Tamil", "Kannada", "Hindi"])
    if st.button("🚀 JOIN NOW"):
        st.query_params.update(room=room_id, role="receiver", ml=my_lang, active="true")
        st.rerun()

else:
    # --- ACTIVE CALL SCREEN ---
    lmap = {"Tamil":"ta", "English":"en", "Kannada":"kn", "Hindi":"hi"}
    my_lang = st.selectbox("My Language:", list(lmap.keys()), key="user_lang")
    
    # Register my settings
    supabase.table("call_messages").upsert({"room_id": room_id, "sender_role": f"{role}_settings", "message_text": my_lang}).execute()

    @st.fragment(run_every=2)
    def inbox_manager():
        other_role = "receiver" if role == "sender" else "sender"
        try:
            # Get latest message
            res = supabase.table("call_messages").select("*").eq("room_id", room_id).eq("sender_role", other_role).order("created_at", desc=True).limit(1).execute()
            
            if res.data:
                msg = res.data[0]
                if msg["id"] not in st.session_state.played_ids:
                    st.markdown(f'<div style="background:#e8f5e9;padding:20px;border-radius:15px;border-left:8px solid #4caf50;"><b>Partner:</b><br><h3>{msg["message_text"]}</h3></div>', unsafe_allow_html=True)
                    play_voice(msg["id"], msg["message_text"], lmap[my_lang])
            else:
                st.info("⌛ Listening for partner...")
        except:
            pass

    inbox_manager()
    st.divider()

    # Voice Recording
    aud = mic_recorder(start_prompt="🎤 START SPEAKING", stop_prompt="⏹️ SEND MESSAGE", key="mic")
    
    if aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(aud['bytes'])
            tmp_path = tmp.name
        try:
            with st.spinner("🚀 Translating..."):
                # Use 'translate' task to force Whisper to find English meaning
                result = model.transcribe(tmp_path, language=lmap[my_lang], task="translate", fp16=False)
                eng_text = result['text'].strip()
                
                if eng_text:
                    # Find out what language the partner speaks
                    other_role = "receiver" if role == "sender" else "sender"
                    p_set = supabase.table("call_messages").select("message_text").eq("room_id", room_id).eq("sender_role", f"{other_role}_settings").limit(1).execute()
                    target_lang_name = p_set.data[0]['message_text'] if p_set.data else "English"
                    
                    # Final meaning translation
                    final_msg = eng_text
                    if target_lang_name != "English":
                        final_msg = GoogleTranslator(source='en', target=lmap[target_lang_name]).translate(eng_text)
                    
                    # Send translated meaning to partner
                    supabase.table("call_messages").insert({"room_id": room_id, "sender_role": role, "message_text": final_msg}).execute()
                    st.rerun()
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)

    if st.button("❌ End Call"):
        st.query_params.clear()
        st.rerun()
























