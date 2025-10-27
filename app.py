import streamlit as st
import pandas as pd
import plotly.express as px
import io
import requests
from O365 import Account
from O365 import FileSystemTokenBackend
import json

# ----------------------------
# CONFIGURATION
# ----------------------------
LOG_FOLDER = r"C:\Users\irene.michelle\OneDrive - Apollo Hospitals Enterprise Ltd\Logs\PG Error Logs"  # Change this to your OneDrive Logs folder

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

# ----------------------------
# LOAD ALL FILES RECURSIVELY
# ----------------------------
csv_files = glob.glob(os.path.join(LOG_FOLDER, "**", "*.csv"), recursive=True)
excel_files = glob.glob(os.path.join(LOG_FOLDER, "**", "*.xlsx"), recursive=True)
all_files = csv_files + excel_files

if not all_files:
    st.warning("No log files found in the OneDrive folder.")
    st.stop()

dfs = []
for file in all_files:
    try:
        if file.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        # ✅ Remove unnamed columns
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

        # ✅ Determine region based on file name
        region_name = "Unknown"
        for keyword, region in region_map.items():
            if keyword.lower() in os.path.basename(file).lower():
                region_name = region
                break

        # ✅ Add Region column
        df["Region"] = region_name

        dfs.append(df)
    except Exception as e:
        st.error(f"Error reading {file}: {e}")

data = pd.concat(dfs, ignore_index=True)
st.success(f"Loaded {len(all_files)} files with {len(data)} rows.")

# ----------------------------
# DATA PREPARATION
# ----------------------------
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

# Export button
def convert_df(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Filtered Logs')
    processed_data = output.getvalue()
    return processed_data

# Custom CSS for download button
st.markdown("""
    <style>
        [data-testid="stDownloadButton"] {
            background-color: #2C3E50 !important;
            color: white !important;
            padding: 10px 20px !important;
            border-radius: 5px !important;
            border: 1px solid #34495E !important;
            font-weight: bold !important;
            transition: all 0.3s ease !important;
        }
        [data-testid="stDownloadButton"]:hover {
            background-color: #34495E !important;
            border-color: #4B9BE6 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
        }
        div.stDownloadButton > button {
            width: auto !important;
            margin: 0 auto !important;
            display: block !important;
        }
    </style>
""", unsafe_allow_html=True)

# Center-aligned container for download button
col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.download_button(
        label="📥 Download Filtered Data as Excel",
        data=convert_df(filtered_data),
        file_name="filtered_logs.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Initial visualizations
if 'Datetime' in filtered_data.columns:
    # Extract hour and create hour labels with AM/PM
    filtered_data['Hour'] = filtered_data['Datetime'].dt.hour
    filtered_data['Hour_Label'] = filtered_data['Hour'].apply(
        lambda x: f"{x if x <= 12 else x-12}:00 {('AM' if x < 12 else 'PM')}"
    )
    
    # Count errors by hour
    hourly_counts = filtered_data.groupby(['Hour', 'Hour_Label']).size().reset_index(name='Count')
    hourly_counts = hourly_counts.sort_values('Hour')
    
    st.markdown("""
        <div style='background-color: #1e1e1e; padding: 15px; border-left: 6px solid #00ccff; margin: 25px 0px;'>
            <h2 style='color: #00ccff; margin:0; font-size: 24px;'>📈 Error Frequency by Hour</h2>
        </div>
    """, unsafe_allow_html=True)
    
    # Create the bar chart
    fig1 = px.bar(
        hourly_counts,
        x='Hour_Label',
        y='Count',
        title="Error Distribution Across Hours of the Day",
        labels={'Hour_Label': 'Hour of Day', 'Count': 'Number of Errors'},
        color='Count',
        color_continuous_scale='Viridis'
    )
    
    # Update layout for better readability
    fig1.update_layout(
        xaxis_title="Hour of Day",
        yaxis_title="Number of Errors",
        xaxis={'tickangle': 45},
        showlegend=False
    )
    
    # Display the chart
    st.plotly_chart(fig1, use_container_width=True)

if 'Exception' in filtered_data.columns:
    st.markdown("""
        <div style='background-color: #1e1e1e; padding: 15px; border-left: 6px solid #8B0000; margin: 25px 0px;'>
            <h2 style='color: #8B0000; margin:0; font-size: 24px;'>⚠️ Top Error Types</h2>
        </div>
    """, unsafe_allow_html=True)
    
    # Calculate error statistics
    total_errors = len(filtered_data)
    error_counts = filtered_data['Exception'].value_counts()
    top_10_errors = error_counts.nlargest(10)
    
    # Create dataframe for visualization
    error_df = pd.DataFrame({
        'Error Type': top_10_errors.index,
        'Count': top_10_errors.values
    })
    
    # Create enhanced bar chart
    fig2 = px.bar(
        error_df,
        x='Error Type',
        y='Count',
        title="Top 10 Error Types",
        labels={'Error Type': 'Error Type', 'Count': 'Number of Occurrences'},
        text='Count',  # Display count on bars
        color_discrete_sequence=['#8B0000']  # Dark red color
    )
    
    # Update bar colors and text
    fig2.update_traces(
        textfont=dict(color='white'),  # Make count numbers white for contrast
        marker_line_color='#660000',  # Slightly darker red for bar borders
        marker_line_width=1  # Thin border for definition
    )
    
    # Update layout for better readability
    fig2.update_layout(
        xaxis_title="Error Type",
        yaxis_title="Number of Occurrences",
        xaxis={
            'tickangle': 45,
            'tickfont': {'size': 10},  # Smaller font size for x-axis labels
            'title_standoff': 25  # More space between axis and title
        },
        yaxis={
            'title_standoff': 25  # More space between axis and title
        },
        title={
            'y': 0.95,  # Move title up slightly
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 20}  # Larger font for main title
        },
        margin=dict(
            l=50,    # left margin
            r=50,    # right margin
            t=100,   # top margin
            b=100    # bottom margin
        ),
        height=600,  # Increase overall height of the chart
        showlegend=False
    )
    
    # Display the chart
    st.plotly_chart(fig2, use_container_width=True)

if 'Object Name' in filtered_data.columns:
    st.markdown("""
        <div style='background-color: #1e1e1e; padding: 15px; border-left: 6px solid #DAA520; margin: 25px 0px;'>
            <h2 style='color: #DAA520; margin:0; font-size: 24px;'>🎯 Top Affected Objects</h2>
        </div>
    """, unsafe_allow_html=True)
    obj_counts = filtered_data['Object Name'].value_counts().nlargest(10)
    obj_df = pd.DataFrame({
        'Object Name': obj_counts.index,
        'Count': obj_counts.values
    })
    fig3 = px.bar(
        obj_df,
        x='Object Name',
        y='Count',
        title="Top 10 Objects",
        text='Count',  # Display count on bars
        color_discrete_sequence=['#DAA520']  # Golden Rod/Deep Mustard color
    )
    
    # Update bar appearance
    fig3.update_traces(
        textfont=dict(color='white'),  # Make count numbers white for contrast
        marker_line_color='#B8860B',  # Slightly darker golden color for bar borders
        marker_line_width=1  # Thin border for definition
    )
    
    # Update layout for better readability and spacing
    fig3.update_layout(
        xaxis_title="Object Name",
        yaxis_title="Number of Occurrences",
        xaxis={
            'tickangle': 45,
            'tickfont': {'size': 10},  # Smaller font size for x-axis labels
            'title_standoff': 25  # More space between axis and title
        },
        yaxis={
            'title_standoff': 25  # More space between axis and title
        },
        title={
            'y': 0.95,  # Move title up slightly
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 20}  # Larger font for main title
        },
        margin=dict(
            l=50,    # left margin
            r=50,    # right margin
            t=100,   # top margin
            b=100    # bottom margin
        ),
        height=600,  # Increase overall height of the chart
        showlegend=False
    )
    
    st.plotly_chart(fig3, use_container_width=True)

if 'Region' in filtered_data.columns:
    st.markdown("""
        <div style='background-color: #1e1e1e; padding: 15px; border-left: 6px solid #00CED1; margin: 25px 0px;'>
            <h2 style='color: #00CED1; margin:0; font-size: 24px;'>📍 Logs by Region</h2>
        </div>
    """, unsafe_allow_html=True)
    region_counts = filtered_data['Region'].value_counts()
    
    # Create pie chart with vibrant colors suitable for dark background
    fig4 = px.pie(
        values=region_counts.values, 
        names=region_counts.index, 
        title="Logs Distribution by Region",
        color_discrete_sequence=[
            '#00CED1',  # Dark Turquoise
            '#FF4500',  # Orange Red
            '#9370DB',  # Medium Purple
            '#32CD32',  # Lime Green
            '#FF69B4',  # Hot Pink
            '#4169E1',  # Royal Blue
            '#FFD700',  # Gold
            '#FF6347',  # Tomato
            '#7B68EE',  # Medium Slate Blue
            '#20B2AA',  # Light Sea Green
        ]
    )
    
    # Update layout and appearance
    fig4.update_layout(
        title={
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 20}
        },
        # Increase margins to prevent overlap
        margin=dict(
            l=50,
            r=50,
            t=100,
            b=50
        ),
        height=600,  # Increase height
        legend={
            'orientation': 'h',  # Horizontal legend
            'yanchor': 'bottom',
            'y': -0.2,  # Place legend below the pie chart
            'xanchor': 'center',
            'x': 0.5,
            'font': {'size': 12}
        }
    )
    
    # Update traces for better visibility
    fig4.update_traces(
        textinfo='label+percent',  # Show label and percentage
        textfont_size=14,
        textfont_color='white',  # White text for better contrast
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>"
    )
    
    st.plotly_chart(fig4, use_container_width=True)

# ----------------------------
# FILTERS
# ----------------------------

# Initialize session state for filters if not exists
if 'date_filter_type' not in st.session_state:
    st.session_state.date_filter_type = "Single Date"
if 'date_selection' not in st.session_state:
    st.session_state.date_selection = None
if 'include_error_types' not in st.session_state:
    st.session_state.include_error_types = []
if 'exclude_error_types' not in st.session_state:
    st.session_state.exclude_error_types = []
if 'objects' not in st.session_state:
    st.session_state.objects = []
if 'regions' not in st.session_state:
    st.session_state.regions = []
if 'search_term' not in st.session_state:
    st.session_state.search_term = ""

# Custom CSS for filters section
st.markdown("""
    <style>
        .filter-section {
            background-color: #1E1E1E;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .filter-header {
            color: #4B9BE6;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .stRadio > label {
            color: #E0E0E0 !important;
        }
        .stMultiSelect > label {
            color: #E0E0E0 !important;
        }
        .stDateInput > label {
            color: #E0E0E0 !important;
        }
        div[data-baseweb="select"] > div {
            background-color: #2C3E50 !important;
            border-color: #34495E !important;
        }
        div[data-baseweb="select"] span {
            color: #E0E0E0 !important;
        }
        .stTextInput > label {
            color: #E0E0E0 !important;
        }
        .stTextInput > div > div > input {
            background-color: #2C3E50 !important;
            color: #E0E0E0 !important;
            border-color: #34495E !important;
        }
    </style>
""", unsafe_allow_html=True)

# Filters header with custom styling
st.sidebar.markdown("""
    <div style='background-color: #1E1E1E; padding: 15px; border-left: 6px solid #4B9BE6; margin: 10px 0px;'>
        <h2 style='color: #4B9BE6; margin:0; font-size: 24px;'>🔍 Filters</h2>
    </div>
""", unsafe_allow_html=True)

# Create a form for filters
with st.sidebar.form("filter_form"):
    # Date filter
    if 'Datetime' in data.columns:
        max_date = data['Datetime'].max()
        min_date = data['Datetime'].min()
        
        # Set default date range to last 2 days to match initial data load
        default_end_date = max_date
        default_start_date = max_date - pd.Timedelta(days=2)
        
        # Ensure default_start_date is not earlier than the earliest available date
        default_start_date = max(default_start_date, min_date)
        
        # Add radio button for date selection type
        st.session_state.date_filter_type = st.radio(
            "Date Filter Type",
            ["Single Date", "Date Range"],
            horizontal=True
        )
        
        if st.session_state.date_filter_type == "Single Date":
            single_date = st.date_input(
                "Select Date",
                value=default_end_date.date(),
                min_value=min_date.date(),
                max_value=max_date.date()
            )
            st.session_state.date_selection = [single_date, single_date]  # Same date for start and end
        else:
            st.session_state.date_selection = st.date_input(
                "Select Date Range", 
                [default_start_date.date(), default_end_date.date()],
                min_value=min_date.date(),
                max_value=max_date.date()
            )

    # Error type filter
    if 'Exception' in data.columns:
        all_error_types = sorted(data['Exception'].dropna().unique())
        
        # Create multiselect for including error types
        st.session_state.include_error_types = st.multiselect(
            "🔍 Search and Select Error Types",
            options=all_error_types,
            default=[],
            key="include_error_multiselect",
            placeholder="Type to search errors to include..."
        )
        
        # Create multiselect for excluding error types
        st.session_state.exclude_error_types = st.multiselect(
            "❌ Exclude Error Types",
            options=all_error_types,
            default=[],
            key="exclude_error_multiselect",
            placeholder="Type to search errors to exclude..."
        )
        
        # Show only active selections
        col1, col2 = st.columns(2)
        
        with col1:
            if len(st.session_state.include_error_types) > 0:
                st.markdown(f"""
                    <div style='text-align: center;'>
                        <span style='color: #3498db; font-size: 15px;'>📋 Including {len(st.session_state.include_error_types)}</span>
                    </div>
                """, unsafe_allow_html=True)
                
        with col2:
            if len(st.session_state.exclude_error_types) > 0:
                st.markdown(f"""
                    <div style='text-align: center;'>
                        <span style='color: #E74C3C; font-size: 15px;'>❌ Excluding {len(st.session_state.exclude_error_types)}</span>
                    </div>
                """, unsafe_allow_html=True)

    # Object name filter
    if 'Object Name' in data.columns:
        st.session_state.objects = st.multiselect(
            "Select Object Names", 
            options=data['Object Name'].dropna().unique()
        )

    # Region filter
    if 'Region' in data.columns:
        st.session_state.regions = st.multiselect(
            "Select Regions", 
            options=data['Region'].dropna().unique()
        )

    # Search bar
    st.markdown("<br>", unsafe_allow_html=True)
    st.session_state.search_term = st.text_input("🔎 Search in all columns")
    
    # Submit button
    submitted = st.form_submit_button("🚀 GO", type="primary", use_container_width=True)

# Custom CSS for the GO button with eggplant purple
st.markdown("""
    <style>
        .stButton > button {
            background-color: #483248 !important;
            color: white !important;
            border: none !important;
        }
        .stButton > button:hover {
            background-color: #3c2a3c !important;
        }
    </style>
""", unsafe_allow_html=True)

if submitted:
    # Show processing message
    processing_message = st.empty()
    processing_message.info("⏳ Processing filters...")
    
    # Apply filters
    filtered_data = data.copy()
    
    # Date filter
    if st.session_state.date_selection and len(st.session_state.date_selection) == 2:
        start_date, end_date = st.session_state.date_selection
        filtered_data = filtered_data[(filtered_data['Datetime'] >= pd.to_datetime(start_date)) & 
                        (filtered_data['Datetime'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))]
    
    # Error type filters
    if st.session_state.include_error_types:
        filtered_data = filtered_data[filtered_data['Exception'].isin(st.session_state.include_error_types)]
    if st.session_state.exclude_error_types:
        filtered_data = filtered_data[~filtered_data['Exception'].isin(st.session_state.exclude_error_types)]
    
    # Object filter
    if st.session_state.objects:
        filtered_data = filtered_data[filtered_data['Object Name'].isin(st.session_state.objects)]
    
    # Region filter
    if st.session_state.regions:
        filtered_data = filtered_data[filtered_data['Region'].isin(st.session_state.regions)]
    
    # Search term filter
    if st.session_state.search_term:
        filtered_data = filtered_data[filtered_data.apply(lambda row: row.astype(str).str.contains(st.session_state.search_term, case=False).any(), axis=1)]
    
    # Update session state with filtered data
    st.session_state.filtered_data = filtered_data
    st.rerun()