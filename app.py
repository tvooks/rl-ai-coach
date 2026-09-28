import streamlit as st
import json
import time
import struct
import io
from google import genai

# --- SAFE PURE PYTHON ROCKET LEAGUE REPLAY PARSER ---
class SafeRLReplayParser:
    def __init__(self, data: bytes):
        self.stream = io.BytesIO(data)

    def safe_read(self, n: int):
        b = self.stream.read(n)
        if len(b) < n:
            return None
        return b

    def read_int32(self):
        b = self.safe_read(4)
        return struct.unpack("<i", b)[0] if b else 0

    def read_uint32(self):
        b = self.safe_read(4)
        return struct.unpack("<I", b)[0] if b else 0

    def read_uint64(self):
        b = self.safe_read(8)
        return struct.unpack("<Q", b)[0] if b else 0

    def read_float32(self):
        b = self.safe_read(4)
        return struct.unpack("<f", b)[0] if b else 0.0

    def read_string(self):
        length_bytes = self.safe_read(4)
        if not length_bytes:
            return ""
        length = struct.unpack("<i", length_bytes)[0]
        
        if length == 0 or abs(length) > 10000:
            return ""
            
        if length > 0:
            val_bytes = self.safe_read(length)
            if not val_bytes:
                return ""
            if val_bytes.endswith(b'\x00'):
                val_bytes = val_bytes[:-1]
            return val_bytes.decode("utf-8", errors="replace")
        else:
            val_bytes = self.safe_read(-length * 2)
            if not val_bytes:
                return ""
            if val_bytes.endswith(b'\x00\x00'):
                val_bytes = val_bytes[:-2]
            return val_bytes.decode("utf-16le", errors="replace")

    def parse_properties(self):
        props = {}
        while True:
            try:
                name = self.read_string()
                if not name or name == "None":
                    break
                type_name = self.read_string()
                size = self.read_uint64()
                
                if type_name == "IntProperty":
                    props[name] = self.read_int32()
                elif type_name in ["StrProperty", "NameProperty"]:
                    props[name] = self.read_string()
                elif type_name == "FloatProperty":
                    props[name] = round(self.read_float32(), 2)
                elif type_name == "QWordProperty":
                    props[name] = self.read_uint64()
                elif type_name == "BoolProperty":
                    val = self.safe_read(1)
                    props[name] = bool(val[0]) if val else False
                elif type_name == "ByteProperty":
                    enum_name = self.read_string()
                    if enum_name == "None" or not enum_name:
                        b = self.safe_read(1)
                        props[name] = b[0] if b else 0
                    else:
                        props[name] = self.read_string()
                elif type_name == "ArrayProperty":
                    count = self.read_int32()
                    arr = []
                    for _ in range(max(0, min(count, 200))):
                        elem = self.parse_properties()
                        if elem is not None:
                            arr.append(elem)
                    props[name] = arr
                else:
                    if 0 < size < 10_000_000:
                        self.safe_read(size)
            except Exception:
                break
        return props

    def parse_header(self):
        try:
            _header_size = self.read_uint32()
            _crc = self.read_uint32()
            engine_ver = self.read_uint32()
            licensee_ver = self.read_uint32()
            if engine_ver >= 868 and licensee_ver >= 18:
                _net_ver = self.read_uint32()
            _replay_type = self.read_string()
            return self.parse_properties()
        except Exception as e:
            return {"parsing_error": str(e)}

# --- PAGE SETUP ---
st.set_page_config(page_title="Rocket League AI Coach", page_icon="⚽", layout="centered")
st.title("⚽ Rocket League AI Coach")
st.write("Upload a raw Rocket League `.replay` file directly to get instant AI coaching advice.")

# --- SIDEBAR: CONFIGURATION ---
st.sidebar.header("🔑 Setup")
gemini_api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key", type="password", help="Get your free key at aistudio.google.com")

st.sidebar.markdown("---")
player_rank = st.sidebar.selectbox("Your Current Rank", ["Gold/Platinum", "Diamond", "Champion 1 - 2", "Champion 3 / GC1", "GC2+", "SSL / 2000+ MMR"])
target_player = st.sidebar.text_input("Your In-Game Name (Optional)", help="Enter your exact in-game name so the AI knows who to analyze.")

# --- AI COACHING GENERATION ---
def generate_coaching_report(telemetry_data, rank, target_name, api_key):
    client = genai.Client(api_key=api_key)
    
    player_focus = f"Focus particularly on analyzing player '{target_name}'." if target_name else "Analyze the main players in the match."
    
    telemetry_json = json.dumps(telemetry_data, indent=2, ensure_ascii=True, default=str)
    
    prompt = f"""
    You are an elite Rocket League Coach evaluating a {rank} player match.
    {player_focus}
    
    Match Metadata from Rocket League Replay Header:
    {telemetry_json}

    Provide a structured coaching report following this format:
    1. **Primary Tactical Error:** What core mistake is holding them back in {rank}?
    2. **Stats Breakdown:** Evaluate key game stats (goals, saves, shots, score, player stats) from the replay telemetry.
    3. **Boost & Positioning Advice:** Recommendations on match rotation, positioning, and resource management.
    4. **Custom Training Plan:** Recommend 2-3 specific workshop maps or custom training concepts suitable for {rank}.
    """
    
    # Updated to latest active models
    models_to_try = ["gemini-3.8-flash", "gemini-2.5-flash"]
    last_error = None
    
    for model in models_to_try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                last_error = e
                time.sleep(1)
                
    raise last_error

# --- MAIN UI FLOW ---
uploaded_file = st.file_uploader("Drop your Rocket League `.replay` file here", type=["replay"])

if uploaded_file is not None:
    st.success(f"File loaded: **{uploaded_file.name}**")
    
    if st.button("🚀 Analyze Replay", type="primary", use_container_width=True):
        if not gemini_api_key:
            st.warning("Please enter your Gemini API Key in the sidebar or save it in Streamlit Secrets.")
        else:
            with st.spinner("Parsing binary `.replay` header..."):
                try:
                    file_bytes = uploaded_file.getvalue()
                    parser = SafeRLReplayParser(file_bytes)
                    replay_metadata = parser.parse_header()
                    
                    with st.spinner("Generating AI coaching report with Gemini..."):
                        report = generate_coaching_report(replay_metadata, player_rank, target_player, gemini_api_key)
                        st.subheader("📋 AI Coaching Analysis")
                        st.markdown(report)
                        
                except Exception as e:
                    st.error(f"Error reading replay file: {e}")
