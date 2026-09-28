import streamlit as st
import requests
import json
import time
from google import genai

st.set_page_config(page_title="Rocket League One-Click AI Coach", page_icon="⚽")
st.title("⚽ Rocket League One-Click AI Coach")

ballchasing_token = st.secrets.get("BALLCHASING_TOKEN") or st.sidebar.text_input("Ballchasing API Token", type="password")
gemini_api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key", type="password")
player_rank = st.sidebar.selectbox("Current Rank", ["Diamond 3", "Champion 1-2", "Champion 3 / GC1", "GC2+"])

def process_replay_and_analyze(replay_bytes, filename, rank, bc_token, gemini_key):
    # Step 1: Upload raw .replay file to Ballchasing API
    upload_url = "https://ballchasing.com/api/v2/upload"
    headers = {"Authorization": bc_token}
    files = {"file": (filename, replay_bytes)}
    
    st.info("Uploading .replay file to telemetry parser...")
    response = requests.post(upload_url, headers=headers, files=files)
    
    if response.status_code == 201:
        replay_id = response.json()["id"]
    elif response.status_code == 409: # Replay already exists on Ballchasing
        replay_id = response.json()["id"]
    else:
        st.error(f"Failed to process replay: {response.text}")
        return None

    # Step 2: Fetch detailed telemetry JSON from Ballchasing
    st.info("Extracting match telemetry...")
    time.sleep(2) # Give Ballchasing a moment to calculate stats
    stats_url = f"https://ballchasing.com/api/replays/{replay_id}"
    stats_response = requests.get(stats_url, headers=headers)
    telemetry_data = stats_response.json()

    # Step 3: Send parsed telemetry straight to Gemini AI
    st.info("Generating AI Coaching Report...")
    client = genai.Client(api_key=gemini_key)
    
    prompt = f"""
    You are an elite Rocket League Coach. Analyze this raw match telemetry JSON for a {rank} player.
    
    Match Data:
    {json.dumps(telemetry_data, indent=2)}

    Provide a structured coaching report:
    1. **Primary Mistake Holding Them Back:** What is keeping them stuck in {rank}?
    2. **Positional & Rotational Breakdown:** Evaluate time spent in defensive third, supersonic speed ratio, and overcommits.
    3. **Boost Efficiency:** Detail boost wasted, stolen, and zero-boost duration.
    4. **Custom Workshop Map & Training Plan:** Recommend 2 specific Workshop maps or training packs for this rank.
    """

    ai_response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    return ai_response.text

# --- UI LOGIC ---
uploaded_replay = st.file_uploader("Drop your `.replay` file here", type=["replay"])

if uploaded_replay and st.button("🚀 Analyze Replay Now", type="primary"):
    if not ballchasing_token or not gemini_api_key:
        st.warning("Please provide both API keys in the sidebar.")
    else:
        replay_bytes = uploaded_replay.read()
        report = process_replay_and_analyze(replay_bytes, uploaded_replay.name, player_rank, ballchasing_token, gemini_api_key)
        if report:
            st.subheader("📋 AI Coaching Analysis")
            st.markdown(report)
