import streamlit as st
import pandas as pd
import json
import time
import tempfile
import os
from google import genai
from google.genai import types

# --- PAGE SETUP ---
st.set_page_config(page_title="Rocket League Hybrid AI Coach", page_icon="⚽", layout="wide")
st.title("⚽ Rocket League Hybrid AI Coach")
st.write("Upload your gameplay video and Ballchasing CSV for a complete tactical and statistical breakdown.")

# --- SIDEBAR: CONFIGURATION ---
st.sidebar.header("🔑 API Credentials & Setup")
gemini_api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key", type="password", help="Get your key at aistudio.google.com")

st.sidebar.markdown("---")
player_rank = st.sidebar.selectbox("Select Your Current Rank", ["Gold/Platinum", "Diamond", "Champion 1 - 2", "Champion 3 / GC1", "GC2+"])
target_player = st.sidebar.text_input("Player Name to Analyze (Optional)", help="Leave blank to analyze all players or enter your specific in-game name.")

# --- AI GENERATION FUNCTION ---

def generate_hybrid_coaching_report(df, video_file_path, rank, target_name, api_key):
    client = genai.Client(api_key=api_key)
    
    # 1. Prepare the CSV Data
    csv_json_data = df.to_dict(orient="records") if df is not None else "No CSV provided."
    player_focus = f"Focus particularly on the player named '{target_name}'." if target_name else "Analyze the main player's POV."
    
    # 2. Upload Video to Gemini
    video_gemini_file = None
    if video_file_path:
        with st.spinner("Uploading video to Gemini's vision engine... this may take a minute."):
            video_gemini_file = client.files.upload(file=video_file_path)
            
            # Wait for Google to process the video frames
            while video_gemini_file.state.name == "PROCESSING":
                time.sleep(3)
                video_gemini_file = client.files.get(name=video_gemini_file.name)
                
            if video_gemini_file.state.name == "FAILED":
                st.error("Video processing failed on Google's servers.")
                return None

    # 3. Master Prompt (We will expand this later with your specific notes)
    prompt = f"""
    You are an elite Rocket League Coach evaluating a {rank} player. 
    {player_focus}
    
    You have been provided with:
    1. A gameplay video of the match.
    2. Telemetry CSV data from Ballchasing.
    
    CSV Data:
    {json.dumps(csv_json_data, indent=2) if df is not None else "None"}

    Watch the video closely and cross-reference it with the CSV data (if available). Provide a structured coaching report following this format:
    
    1. **The Brutal Truth:** What is the primary reason this player is stuck in {rank}?
    2. **Tactical Review (Video Analysis):** Point out specific overcommits, poor spacing, or bad challenges you observed. Give timestamps if possible.
    3. **Mechanical Review (Video Analysis):** Evaluate their mechanics. Are they attempting things outside their capability (e.g., flip resets, bad aerials)? What should they stop doing?
    4. **Efficiency Review (CSV Analysis):** Note boost wastage, time at 0 boost, or slow rotational speed based on the stats.
    5. **The Training Regimen:** Suggest 2-3 specific workshop maps or custom training packs tailored directly to fixing the mistakes you observed in the video.
    """
    
    # 4. Generate Content (Fallback logic included)
    contents_to_send = [prompt]
    if video_gemini_file:
        contents_to_send.append(video_gemini_file)
        
    models_to_try = ["gemini-3.8-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    last_error = None
    
    for model_name in models_to_try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents_to_send
                )
                return response.text
            except Exception as e:
                last_error = e
                time.sleep(2)
                
    raise last_error


# --- MAIN UI FLOW ---

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Upload Video (POV)")
    uploaded_video = st.file_uploader("Drop your MP4/MOV screen recording here", type=["mp4", "mov"])

with col2:
    st.subheader("2. Upload Stats (CSV)")
    uploaded_csv = st.file_uploader("Drop your Ballchasing `.csv` file here", type=["csv"])

if st.button("🚀 Analyze Hybrid Match Data", type="primary", use_container_width=True):
    if not gemini_api_key:
        st.warning("Please enter your Gemini API Key in the sidebar.")
    elif not uploaded_video and not uploaded_csv:
        st.warning("Please upload at least a video or a CSV file.")
    else:
        # Load CSV if available
        df = None
        if uploaded_csv:
            df = pd.read_csv(uploaded_csv)
            
        # Handle Video temp storage
        video_path = None
        if uploaded_video:
            # Save the uploaded file to a temporary location so Gemini can upload it
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
                temp_video.write(uploaded_video.read())
                video_path = temp_video.name
                
        try:
            with st.spinner("Analyzing Match... (This takes a few moments for video)"):
                report = generate_hybrid_coaching_report(df, video_path, player_rank, target_player, gemini_api_key)
                
            if report:
                st.subheader("📋 Hybrid Coaching Report")
                st.markdown(report)
                
        except Exception as e:
            st.error(f"Error generating report: {e}")
            
        finally:
            # Clean up the temporary video file from the server
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
