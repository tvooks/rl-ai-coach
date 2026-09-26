import streamlit as st
import pandas as pd
import json
import time
from google import genai

# --- PAGE SETUP ---
st.set_page_config(page_title="Rocket League CSV AI Coach", page_icon="⚽", layout="centered")
st.title("⚽ Rocket League CSV AI Coach")
st.write("Upload a match CSV report exported from Ballchasing.com to generate AI coaching advice.")

# --- SIDEBAR: CONFIGURATION ---
st.sidebar.header("🔑 API Credentials & Setup")
gemini_api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key", type="password", help="Get your key at aistudio.google.com")

st.sidebar.markdown("---")
player_rank = st.sidebar.selectbox("Select Your Current Rank", ["Gold/Platinum", "Diamond", "Champion 1 - 2", "Champion 3 / GC1", "GC2+"])
target_player = st.sidebar.text_input("Player Name to Analyze (Optional)", help="Leave blank to analyze all players or enter your specific in-game name.")

# --- AI GENERATION FUNCTION WITH RETRY & FALLBACK LOGIC ---

def generate_csv_coaching_report(df, rank, target_name, api_key):
    """Converts CSV data into structured text and sends it to Gemini with automated fallback logic."""
    client = genai.Client(api_key=api_key)
    
    # Convert CSV dataframe to dict/JSON for clean prompt insertion
    csv_json_data = df.to_dict(orient="records")
    
    player_focus = f"Focus particularly on the player named '{target_name}'." if target_name else "Analyze all players on the team."
    
    prompt = f"""
    You are an elite Rocket League Coach. Analyze the following match telemetry CSV data exported from Ballchasing.com for a game played at the '{rank}' rank level.
    {player_focus}
    
    CSV Telemetry Data:
    {json.dumps(csv_json_data, indent=2)}

    Provide a structured coaching report following this format:
    1. **Overview & Match Pace:** How fast was the game played compared to benchmark expectations for {rank}?
    2. **Boost Efficiency & Positioning Breakdown:** Identify high time spent at 0 boost, boost wasted/stolen, or passive defensive time.
    3. **Key Weaknesses Identified:** List 2-3 critical operational mistakes found in the numbers.
    4. **Recommended Training & Workshop Maps:** Suggest 2 specific Workshop maps or custom training pack concepts (e.g., 'Hornets Audio Pack' for saves, 'CoCo's Aim Training', dribbling/shadow defense maps) tailored to these weaknesses.
    """
    
    # List of models to try in order if Google servers experience high demand
    models_to_try = [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-3.8-flash"
    ]
    
    last_error = None
    
    # Loop through models with backoff retry logic
    for model_name in models_to_try:
        for attempt in range(2):  # Try each model up to twice
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                last_error = e
                time.sleep(2)  # Pause briefly before retrying or switching models
                
    raise last_error


# --- MAIN UI FLOW ---

uploaded_csv = st.file_uploader("Drop your Ballchasing `.csv` report file here", type=["csv"])

if uploaded_csv is not None:
    try:
        df = pd.read_csv(uploaded_csv)
        st.success(f"Successfully loaded CSV: **{uploaded_csv.name}** ({len(df)} rows)")
        
        with st.expander("📊 View Uploaded CSV Table"):
            st.dataframe(df)
            
        if st.button("🚀 Analyze CSV Match Data", type="primary"):
            if not gemini_api_key:
                st.warning("Please enter your Gemini API Key in the sidebar or save it in Streamlit Secrets.")
            else:
                with st.spinner("Analyzing CSV telemetry with Gemini AI..."):
                    report = generate_csv_coaching_report(df, player_rank, target_player, gemini_api_key)
                    
                st.subheader("📋 Coaching Report")
                st.markdown(report)
                
    except Exception as e:
        st.error(f"Error reading CSV file: {e}")
