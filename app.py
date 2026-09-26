import streamlit as st
import requests
import time
import json
from google import genai

# --- PAGE SETUP ---
st.set_page_config(page_title="Rocket League AI Coach", page_icon="⚽", layout="centered")
st.title("⚽ Rocket League Replay AI Coach")
st.write("Upload a `.replay` file to fetch telemetry stats from Ballchasing.com and generate AI coaching advice.")

# --- SIDEBAR: API KEYS ---
st.sidebar.header("🔑 API Credentials")
ballchasing_token = st.sidebar.text_input("Ballchasing.com API Token", type="password", help="Find your token at ballchasing.com/upload")
gemini_api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Get your key at aistudio.google.com")

st.sidebar.markdown("---")
player_rank = st.sidebar.selectbox("Select Your Current Rank", ["Gold/Platinum", "Diamond", "Champion 1 - 2", "Champion 3 / GC1", "GC2+"])

# --- CORE FUNCTIONS ---

def upload_and_parse_replay(file_bytes, filename, token):
    """Uploads .replay file to ballchasing.com and fetches full stat breakdown."""
    upload_url = "https://ballchasing.com/api/v2/upload?visibility=public"
    headers = {"Authorization": token}
    files = {"file": (filename, file_bytes)}
    
    # Step 1: Upload Replay
    response = requests.post(upload_url, headers=headers, files=files)
    
    if response.status_code in [201, 409]:
        replay_id = response.json()["id"]
    else:
        st.error(f"Failed to upload replay. Ballchasing API Error: {response.text}")
        return None

    # Step 2: Fetch Summary Stats
    # Ballchasing needs a second or two to parse the file after upload
    time.sleep(3) 
    stats_url = f"https://ballchasing.com/api/replays/{replay_id}"
    stats_response = requests.get(stats_url, headers=headers)
    
    if stats_response.status_code == 200:
        return stats_response.json()
    else:
        st.error("Failed to retrieve replay metrics. Please try again.")
        return None


def extract_telemetry_summary(replay_data):
    """Filters the huge JSON payload into a clean, concise telemetry summary."""
    summary = {}
    
    try:
        # Get team stats
        blue_stats = replay_data.get("blue", {})
        orange_stats = replay_data.get("orange", {})
        
        summary["game_mode"] = replay_data.get("playlist_id", "Unknown")
        summary["duration"] = replay_data.get("duration", 0)
        
        players_data = []
        all_teams = blue_stats.get("players", []) + orange_stats.get("players", [])
        
        for player in all_teams:
            p_stats = player.get("stats", {})
            players_data.append({
                "name": player.get("name"),
                "score": p_stats.get("core", {}).get("score"),
                "goals": p_stats.get("core", {}).get("goals"),
                "saves": p_stats.get("core", {}).get("saves"),
                "shots": p_stats.get("core", {}).get("shots"),
                "boost_collected": p_stats.get("boost", {}).get("amount_collected"),
                "boost_stolen": p_stats.get("boost", {}).get("amount_stolen"),
                "time_zero_boost": p_stats.get("boost", {}).get("time_zero_boost"),
                "time_supersonic": p_stats.get("movement", {}).get("time_supersonic_speed"),
                "avg_speed": p_stats.get("movement", {}).get("avg_speed"),
                "time_defensive_third": p_stats.get("positioning", {}).get("time_defensive_third"),
                "time_offensive_third": p_stats.get("positioning", {}).get("time_offensive_third")
            })
            
        summary["players"] = players_data
        return summary
    except Exception as e:
        st.warning("Parsing warning: Some stats were missing from the replay file.")
        return replay_data


def generate_coaching_report(stats_summary, rank, api_key):
    """Sends telemetry data to Gemini for analysis."""
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    You are an elite Rocket League Coach. Analyze the following match telemetry JSON for a player ranked '{rank}'.
    
    Match Data:
    {json.dumps(stats_summary, indent=2)}

    Provide a structured coaching report following this format:
    1. **Overview & Pace:** How fast was the game played compared to benchmark expectations for {rank}?
    2. **Boost Efficiency & Rotation Mistakes:** Identify players who wasted boost, spent too much time at zero boost, or played overly passive in defense.
    3. **Key Weaknesses Identified:** List 2 critical areas to fix immediately.
    4. **Recommended Training & Workshop Maps:** Suggest 2 specific Workshop maps or custom training pack ideas (e.g., 'Hornets Audio Pack' for saves, 'CoCo's Aim Training', dribbling maps) tailored to these weaknesses.
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text


# --- MAIN UI FLOW ---

uploaded_file = st.file_uploader("Drop your Rocket League `.replay` file here", type=["replay"])

if uploaded_file is not None:
    st.info(f"File uploaded: **{uploaded_file.name}** ({uploaded_file.size / 1000:.1f} KB)")
    
    if st.button("🚀 Analyze Replay", type="primary"):
        if not ballchasing_token or not gemini_api_key:
            st.warning("Please provide both your Ballchasing API Token and Gemini API Key in the sidebar.")
        else:
            with st.spinner("Step 1/3: Uploading replay to Ballchasing.com..."):
                replay_raw = upload_and_parse_replay(uploaded_file.getvalue(), uploaded_file.name, ballchasing_token)
            
            if replay_raw:
                with st.spinner("Step 2/3: Filtering telemetry data..."):
                    clean_stats = extract_telemetry_summary(replay_raw)
                    
                    # Optional: display raw stats expander
                    with st.expander("📊 View Extracted Telemetry Stats"):
                        st.json(clean_stats)

                with st.spinner("Step 3/3: Generating AI Coaching Report..."):
                    coaching_report = generate_coaching_report(clean_stats, player_rank, gemini_api_key)
                    
                st.subheader("📋 Coaching Report")
                st.markdown(coaching_report)
