import streamlit as st
import json
import time
from google import genai

# Try importing native replay parser (sprocket-boxcars-py)
try:
    from boxcars_py import parse_replay
    PARSER_AVAILABLE = True
except ImportError:
    PARSER_AVAILABLE = False

# --- PAGE SETUP ---
st.set_page_config(page_title="Rocket League AI Coach", page_icon="⚽", layout="centered")
st.title("⚽ Rocket League AI Coach")
st.write("Upload a raw Rocket League `.replay` file directly from your computer to get instant AI coaching advice.")

# --- SIDEBAR: CONFIGURATION ---
st.sidebar.header("🔑 API Setup")
gemini_api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key", type="password", help="Get your free key at aistudio.google.com")

st.sidebar.markdown("---")
player_rank = st.sidebar.selectbox("Your Current Rank", ["Gold/Platinum", "Diamond", "Champion 1 - 2", "Champion 3 / GC1", "GC2+", "SSL / 2000+ MMR"])
target_player = st.sidebar.text_input("Your In-Game Name (Optional)", help="Enter your exact in-game name so the AI knows who to analyze.")

# --- HELPER: CLEAN REPLAY DATA FOR GEMINI ---

def clean_replay_structure(raw_replay):
    """Extracts essential header metadata and player stats from parsed boxcars output."""
    if not isinstance(raw_replay, dict):
        return raw_replay

    header = raw_replay.get("header", raw_replay)
    properties = header.get("properties", [])
    
    extracted = {}
    
    # Boxcars structures properties as list pairs [Key, Value]
    if isinstance(properties, list):
        for item in properties:
            if isinstance(item, list) and len(item) == 2:
                key, val_dict = item[0], item[1]
                if isinstance(val_dict, dict):
                    # Unwrap Boxcars type wrappers like {"Int": 3} or {"Str": "park_p"}
                    extracted[key] = list(val_dict.values())[0] if val_dict else None
                else:
                    extracted[key] = val_dict
    elif isinstance(properties, dict):
        extracted = properties
    else:
        extracted = header

    return extracted

# --- AI COACHING GENERATION ---

def generate_coaching_report(telemetry_data, rank, target_name, api_key):
    client = genai.Client(api_key=api_key)
    
    player_focus = f"Focus particularly on analyzing player '{target_name}'." if target_name else "Analyze the main players in the match."
    
    prompt = f"""
    You are an elite Rocket League Coach evaluating a {rank} player match.
    {player_focus}
    
    Match Telemetry Data from Rocket League Replay:
    {json.dumps(telemetry_data, indent=2, default=str)}

    Provide a structured coaching report following this format:
    1. **Primary Tactical Error:** What core mistake is holding them back in {rank}?
    2. **Stats & Positioning Breakdown:** Evaluate key game stats (goals, saves, shots, score, possession/steers) from the telemetry.
    3. **Boost & Pace Control:** Recommendations on match speed, rotation, and resource management.
    4. **Custom Training Plan:** Recommend 2-3 specific workshop maps or training concepts suited for {rank}.
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
        elif not PARSER_AVAILABLE:
            st.error("Replay parser module (`sprocket-boxcars-py`) is not installed. Make sure it is in your requirements.txt file.")
        else:
            with st.spinner("Parsing binary `.replay` file..."):
                try:
                    file_bytes = uploaded_file.read()
                    parsed_raw = parse_replay(file_bytes)
                    cleaned_telemetry = clean_replay_structure(parsed_raw)
                    
                    with st.spinner("Generating AI coaching report with Gemini..."):
                        report = generate_coaching_report(cleaned_telemetry, player_rank, target_player, gemini_api_key)
                        st.subheader("📋 AI Coaching Analysis")
                        st.markdown(report)
                        
                except Exception as e:
                    st.error(f"Error processing replay file: {e}")
