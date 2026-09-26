import streamlit as st
import pandas as pd
import json
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

# --- AI GENERATION FUNCTION ---

def generate_csv_coaching_report(df, rank, target_name, api_key):
    """Converts CSV data into structured text and sends it to Gemini."""
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
    
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )
    return response.text


# --- MAIN UI FLOW ---

uploaded_csv = st.file_uploader("Drop your Ballchasing `.csv` report file here", type=["csv"])

if uploaded_csv is not None:
    # Read the CSV into a Pandas DataFrame
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
