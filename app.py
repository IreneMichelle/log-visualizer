import streamlit as st
import pandas as pd
import plotly.express as px
import io
import requests

# ----------------------------
# CONFIGURATION
# ----------------------------
# GitHub raw URL configuration
GITHUB_BASE_URL = "https://raw.githubusercontent.com/IreneMichelle/log-visualizer/main/data/"

# Define mapping of keywords to region names
region_map = {
    "NSK": "Nashik",
    "BBSR": "Bhubaneswar",
    "BHO": "Bhopal",
    "MUM": "Mumbai",
    "BGLR": "Bangalore",
    "DEL": "Delhi",
    "HYD": "Hyderabad",
    "CHN": "Chennai",
    "KOL": "Kolkata"
}

st.set_page_config(page_title="Log Visualizer", layout="wide")

# Center-aligned title with custom CSS
st.markdown("""
    <h1 style='text-align: center; color: #00ccff;'>
        📊 Log File Visualizer
    </h1>
""", unsafe_allow_html=True)

# Custom CSS for the GO button
st.markdown("""
    <style>
        .stButton > button {
            background-color: #6a0dad !important;
            color: white !important;
        }
        .stButton > button:hover {
            background-color: #551a8b !important;
            color: white !important;
        }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Load data from GitHub raw URLs"""
    try:
        # Get list of files from GitHub repository
        repo_url = "https://api.github.com/repos/IreneMichelle/log-visualizer/contents/data"
        response = requests.get(repo_url)
        response.raise_for_status()
        files = [file['name'] for file in response.json() if file['name'].endswith('.xlsx')]
        
        if not files:
            st.warning("No Excel files found in the data folder.")
            st.stop()
    except Exception as e:
        st.error(f"Error fetching file list from GitHub: {str(e)}")
        st.stop()
    
    dfs = []
    for file in files:
        try:
            file_url = f"{GITHUB_BASE_URL}{file}"
            response = requests.get(file_url)
            response.raise_for_status()  # Check for HTTP errors
            df = pd.read_excel(io.BytesIO(response.content))
            
            # Remove unnamed columns
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            
            # Determine region based on file name
            region_name = "Unknown"
            for keyword, region in region_map.items():
                if keyword.lower() in file.lower():
                    region_name = region
                    break
                    
            # Add Region column
            df["Region"] = region_name
            dfs.append(df)
        except Exception as e:
            st.error(f"Error reading {file}: {str(e)}")
            
    if not dfs:
        st.error("No data could be loaded from any files.")
        st.stop()
        
    data = pd.concat(dfs, ignore_index=True)
    st.success(f"Loaded {len(files)} files with {len(data)} rows.")
    return data

# Load the data
try:
    data = load_data()
    
    # Data preparation
    if 'Datetime' in data.columns:
        data['Datetime'] = pd.to_datetime(data['Datetime'], errors='coerce')

    # Initialize and display default 2-day filtered data
    if 'filtered_data' not in st.session_state:
        filtered_data = data.copy()
        if 'Datetime' in filtered_data.columns:
            end_date = filtered_data['Datetime'].max()
            start_date = end_date - pd.Timedelta(days=2)
            filtered_data = filtered_data[
                (filtered_data['Datetime'] >= pd.to_datetime(start_date)) & 
                (filtered_data['Datetime'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))
            ]
        st.session_state.filtered_data = filtered_data

    # Get current filtered data from session state
    filtered_data = st.session_state.filtered_data

    # Display current data and visualizations
    st.markdown("""
        <div style='background-color: #1e1e1e; padding: 15px; border-left: 6px solid #4B9BE6; margin: 25px 0px;'>
            <h2 style='color: #4B9BE6; margin:0; font-size: 24px;'>🔍 Filtered Data</h2>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"<p style='color: #c6c6c6; margin-bottom: 20px;'>Showing {len(filtered_data)} rows</p>", unsafe_allow_html=True)
    st.dataframe(filtered_data)

except Exception as e:
    st.error(f"Error in data processing: {str(e)}")