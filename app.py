import streamlit as st
import boxcars
import json
from google import genai

# --- PAGE SETUP ---
st.set_page_config(page_title="Rocket League 1-Click AI Coach", page_icon="⚽", layout="centered")
st.title("⚽ Rocket League 1-Click AI Coach")
st.write("Upload a raw `.replay` file directly from your game folder for instant AI coaching.")

# --- SIDEBAR: CONFIGURATION ---
st.sidebar.header("🔑 API Credentials & Setup")
gemini_api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key", type="password", help="Get your key at aistudio.google.com")

st.sidebar.markdown("---")
player_rank = st.sidebar.selectbox("Select Your Current Rank", ["Gold/Platinum", "Diamond", "Champion 1 - 2", "Champion 3 / GC1", "GC2+", "SSL / 2000+ MMR"])
target_player = st.sidebar.text_input("Your In-Game Name", help="Enter your exact in-game name so the AI knows which player to coach.")

# --- LOCAL REPLAY PARSER FUNCTION ---

def parse_replay_locally(file_bytes):
    """Parses raw binary .replay bytes directly in Python without any external API."""
    try:
        # boxcars parses header and frame data directly in memory
        parsed_data = boxcars.parse_replay(file_bytes)
        return json.loads(parsed_data)
    except Exception as e:
        st.error(f"Error parsing replay file: {e}")
        return None

# --- AI COACHING GENERATION ---

def generate_coaching_report(telemetry_data, rank, target_name, api_key):
    client = genai.Client(api_key=api_key)
    
    # Extract header properties (goals, players, stats)
    header_properties = telemetry_data.get("header", {}).get("body", {}).get("properties", {})
    
    player_focus = f"Focus particularly on analyzing the player named '{target_name}'." if target_name else "Analyze the main players in the lobby."
    
    prompt = f"""
    You are an elite Rocket League Coach evaluating a {rank} player.
    {player_focus}
    
    Below is the extracted match telemetry and header data from the raw `.replay` file:
    {json.dumps(header_properties, indent=2)}

    Provide a structured coaching report following this format:
    1. **Primary Mistake Holding Them Back:** What is keeping them stuck in {rank}?
    2. **Positional & Rotational Breakdown:** Evaluate key game stats, goals conceded, and team dynamics.
    3. **Boost & Pace Efficiency:** Identify area of improvement regarding match speed and resource control.
    4. **Custom Training Plan & Workshop Maps:** Recommend 2-3 specific workshop maps or custom training pack concepts suitable for {rank}.
    """
    
    models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash"]
    
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            return response.text
        except Exception:
            continue
            
    raise Exception("Could not connect to Gemini AI models.")

# --- MAIN UI FLOW ---

uploaded_replay = st.file_uploader("Drop your `.replay` file here", type=["replay"])

if uploaded_replay is not None:
    st.success(f"File loaded: **{uploaded_replay.name}**")
    
    if st.button("🚀 Analyze Replay Now", type="primary", use_container_width=True):
        if not gemini_api_key:
            st.warning("Please enter your Gemini API Key in the sidebar or save it in Streamlit Secrets.")
        else:
            with st.spinner("Parsing binary replay & generating AI coaching report..."):
                file_bytes = uploaded_replay.read()
                telemetry = parse_replay_locally(file_bytes)
                
                if telemetry:
                    report = generate_coaching_report(telemetry, player_rank, target_player, gemini_api_key)
                    st.subheader("📋 AI Coaching Analysis")
                    st.markdown(report)
