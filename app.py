import streamlit as st
import numpy as np
import requests
import pandas as pd
from sgp4.api import Satrec, jday
from datetime import datetime, timezone

st.set_page_config(layout="wide", page_title="Live Satellite Tracker")

st.title("🛰️ Universal Live Satellite Tracker")
st.write("Track any active satellite using its 5-digit NORAD Catalog ID.")

# Sidebar Input
st.sidebar.header("Satellite Search")
search_query = st.sidebar.text_input("Enter 5-digit NORAD ID (e.g., 25544 for ISS)", "25544").strip()

# Fetch TLE data cleanly
def fetch_live_tle(norad_id):
    if not norad_id or not norad_id.isdigit():
        return None
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATID={norad_id}&FORMAT=TLE"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and response.text.strip():
            lines = [line.strip() for line in response.text.splitlines() if line.strip()]
            if len(lines) >= 3 and "No data found" not in lines[0]:
                return lines[0], lines[1], lines[2]
    except Exception:
        return None
    return None

if search_query:
    tle_data = fetch_live_tle(search_query)

    if tle_data:
        sat_name, tle_line1, tle_line2 = tle_data
        st.sidebar.success(f"🎯 Tracking Active: {sat_name}")
        
        try:
            # SGP4 Math Engine
            satrec = Satrec.twoline2rv(tle_line1, tle_line2)
            now = datetime.now(timezone.utc)
            jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond / 1e6)
            
            error_code, position, velocity = satrec.sgp4(jd, fr)
            
            if error_code == 0:
                x, y, z = position[0], position[1], position[2]
                lon_deg = float(np.degrees(np.arctan2(y, x)))
                lat_deg = float(np.degrees(np.arctan2(z, np.sqrt(x**2 + y**2))))
                
                # Show Stats
                c1, c2, c3 = st.columns(3)
                c1.metric("Live Latitude", f"{lat_deg:.4f}°")
                c2.metric("Live Longitude", f"{lon_deg:.4f}°")
                c3.metric("Current Time (UTC)", now.strftime('%Y-%m-%d %H:%M:%S'))
                
                st.write("### Live Position Map")
                # Using Streamlit's native high-performance mapping engine 
                # instead of fragile external images/map downloads
                map_data = pd.DataFrame({'lat': [lat_deg], 'lon': [lon_deg]})
                st.map(map_data, zoom=1)
                
                if st.button("🔄 Force Live Refresh Update", use_container_width=True):
                    st.rerun()
            else:
                st.error(f"SGP4 Propagation Error (Code {error_code}).")
        except Exception as e:
            st.error(f"Processing Error: {e}")
    else:
        st.error(f"Could not find or fetch data for NORAD ID: {search_query}")
