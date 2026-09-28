import streamlit as st
import json
import time
import struct
import io
from google import genai

# --- PURE PYTHON ROCKET LEAGUE REPLAY PARSER ---
class RLReplayParser:
    def __init__(self, data: bytes):
        self.stream = io.BytesIO(data)

    def read_int32(self):
        return struct.unpack("<i", self.stream.read(4))[0]

    def read_uint32(self):
        return struct.unpack("<I", self.stream.read(4))[0]

    def read_uint64(self):
        return struct.unpack("<Q", self.stream.read(8))[0]

    def read_float32(self):
        return struct.unpack("<f", self.stream.read(4))[0]

    def read_string(self):
        length_data = self.stream.read(4)
        if not length_data or len(length_data) < 4:
            return ""
        length = struct.unpack("<i", length_data)[0]
        if length == 0:
            return ""
        if length > 0:
            val_bytes = self.stream.read(length)
            return val_bytes[:-1].decode("utf-8", errors="ignore")
        else:
            val_bytes = self.stream.read(-length * 2)
            return val_bytes[:-2].decode("utf-16le", errors="ignore")

    def parse_properties(self):
        props = {}
        while True:
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
                val = self.stream.read(1)
                props[name] = bool(val[0]) if val else False
            elif type_name == "ByteProperty":
                _enum_type = self.read_string()
                enum_val = self.read_string()
                props[name] = enum_val
            elif type_name == "ArrayProperty":
                count = self.read_int32()
                arr = []
                for _ in range(count):
                    arr.append(self.parse_properties())
                props[name] = arr
            else:
                self.stream.read(size)
        return props

    def parse_header(self):
        _header_size = self.read_uint32()
        _crc = self.read_uint32()
        engine_ver = self.read_uint32()
        licensee_ver = self.read_uint32()
        if engine_ver >= 868 and licensee_ver >= 18:
            _net_ver = self.read_uint32()
        _replay_type = self.read_string()
        return self.parse_properties()

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
    
    prompt = f"""
    You are an elite Rocket League Coach evaluating a {rank} player match.
    {player_focus}
    
    Match Metadata from Rocket League Replay:
    {json.dumps(telemetry_data, indent=2, default=str)}

    Provide a structured coaching report following this format:
    1. **Primary Tactical Error:** What core mistake is holding them back in {rank}?
    2. **Stats Breakdown:** Evaluate key game stats (goals, saves, shots, score, player stats) from the replay telemetry.
    3. **Boost & Positioning Advice:** Recommendations on match rotation, positioning, and resource management.
    4. **Custom Training Plan:** Recommend 2-3 specific workshop maps or custom training concepts suitable for {rank}.
    """
    
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    last_error = None
    
    for model in models_to_try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt
                )
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
                    file_bytes = uploaded_file.read()
                    parser = RLReplayParser(file_bytes)
                    replay_metadata = parser.parse_header()
                    
                    with st.spinner("Generating AI coaching report with Gemini..."):
                        report = generate_coaching_report(replay_metadata, player_rank, target_player, gemini_api_key)
                        st.subheader("📋 AI Coaching Analysis")
                        st.markdown(report)
                        
                except Exception as e:
                    st.error(f"Error reading replay file: {e}")
