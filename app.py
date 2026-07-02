import streamlit as st
import numpy as np
import requests
import pandas as pd
from sgp4.api import Satrec, jday
from datetime import datetime, timezone, timedelta

st.set_page_config(layout="wide", page_title="Live Satellite Tracker (UK Time)")

st.title("🛰️ Universal Live Satellite Tracker")
st.write("Track any active satellite using its 5-digit NORAD Catalog ID.")

# Sidebar Input
st.sidebar.header("1. Input Configuration")
input_method = st.sidebar.radio("Choose Input Method:", ("Fetch via NORAD ID", "Paste Raw TLE Text Manually"))

tle_line1 = ""
tle_line2 = ""
sat_name = "Unknown Satellite"

if input_method == "Fetch via NORAD ID":
    norad_id = st.sidebar.text_input("Enter 5-digit NORAD ID (e.g., 25544 for ISS)", "25544").strip()
    
    if st.sidebar.button("🛰️ Fetch Live TLE", use_container_width=True):
        if norad_id.isdigit():
            url = f"https://celestrak.org/NORAD/elements/gp.php?CATID={norad_id}&FORMAT=TLE"
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                response = requests.get(url, headers=headers, timeout=8)
                if response.status_code == 200 and response.text.strip():
                    lines = [l.strip() for l in response.text.splitlines() if l.strip()]
                    if len(lines) >= 3 and "No data found" not in lines[0]:
                        st.session_state['sat_name'] = lines[0]
                        st.session_state['tle1'] = lines[1]
                        st.session_state['tle2'] = lines[2]
                        st.sidebar.success(f"Fetched: {lines[0]}")
            except Exception:
                st.sidebar.error("Network issue. Please try pasting manually.")
                
    sat_name = st.session_state.get('sat_name', 'ISS (ZARYA)')
    tle_line1 = st.session_state.get('tle1', '1 25544U 98067A   24061.62141410  .00015481  00000+0  27533-3 0  9993')
    tle_line2 = st.session_state.get('tle2', '2 25544  51.6416 189.2453 0001324  57.8546  68.2239 15.49479301441113')

else:
    sat_name = st.sidebar.text_input("Satellite Name Label", "Custom Target")
    tle_line1 = st.sidebar.text_input("Line 1", "1 25544U 98067A   24061.62141410  .00015481  00000+0  27533-3 0  9993").strip()
    tle_line2 = st.sidebar.text_input("Line 2", "2 25544  51.6416 189.2453 0001324  57.8546  68.2239 15.49479301441113").strip()

# Run the Tracking computations
st.header("2. Live Tracking Status")

if tle_line1 and tle_line2:
    try:
        satrec = Satrec.twoline2rv(tle_line1, tle_line2)
        
        # SGP4 MUST use strict standard UTC for its physics math
        utc_now = datetime.now(timezone.utc)
        jd, fr = jday(utc_now.year, utc_now.month, utc_now.day, utc_now.hour, utc_now.minute, utc_now.second + utc_now.microsecond / 1e6)
        
        error_code, position, velocity = satrec.sgp4(jd, fr)
        
        if error_code == 0:
            x, y, z = position[0], position[1], position[2]
            lon_deg = float(np.degrees(np.arctan2(y, x)))
            lat_deg = float(np.degrees(np.arctan2(z, np.sqrt(x**2 + y**2))))
            
            # Convert UTC math clock to your local clock presentation (BST/UK Time is +1 hour right now)
            local_uk_time = utc_now + timedelta(hours=1)
            
            # UI display cards
            m1, m2, m3 = st.columns(3)
            m1.metric("Target Satellite", sat_name)
            m2.metric("Calculated Latitude", f"{lat_deg:.4f}°")
            m3.metric("Calculated Longitude", f"{lon_deg:.4f}°")
            
            st.write(f"**Current Tracking Time (Local UK Time):** {local_uk_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Map rendering
            map_df = pd.DataFrame({'lat': [lat_deg], 'lon': [lon_deg]})
            st.map(map_df, zoom=2)
            
            if st.button("🔄 Force Live Coordinate Refresh", use_container_width=True):
                st.rerun()
        else:
            st.error(f"SGP4 Math Error (Code {error_code}).")
    except Exception as e:
        st.error(f"Calculation Error: {e}")
