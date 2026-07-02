import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
import requests
from sgp4.api import Satrec, jday
from datetime import datetime, timezone

st.set_page_config(layout="wide", page_title="Live Satellite Tracker")

st.title("🛰️ Universal Live Satellite Tracker")
st.write("Enter a satellite's 5-digit NORAD Catalog ID to track its exact live position.")

# Sidebar Configuration
st.sidebar.header("Satellite Search")
search_query = st.sidebar.text_input("Enter 5-digit NORAD ID (e.g., 25544, 20580, 33591)", "25544").strip()

# Step 1: Fetching data from Celestrak GP query system
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

# Load the base world map safely
@st.cache_data
def load_world_map():
    try:
        url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_land.geojson"
        return gpd.read_file(url)
    except Exception:
        return gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))

if search_query:
    tle_data = fetch_live_tle(search_query)

    if tle_data:
        sat_name, tle_line1, tle_line2 = tle_data
        st.sidebar.success(f"🎯 Tracking Active: {sat_name}")
        
        try:
            # Step 2: SGP4 Propagation Engine
            satrec = Satrec.twoline2rv(tle_line1, tle_line2)
            now = datetime.now(timezone.utc)
            jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond / 1e6)
            
            error_code, position, velocity = satrec.sgp4(jd, fr)
            
            if error_code == 0:
                # Step 3: Compute Geographic Coordinates
                x, y, z = position[0], position[1], position[2]
                lon_deg = np.degrees(np.arctan2(y, x))
                lat_deg = np.degrees(np.arctan2(z, np.sqrt(x**2 + y**2)))
                
                # Display tracking data cards
                c1, c2, c3 = st.columns(3)
                c1.metric("Live Latitude", f"{lat_deg:.4f}°")
                c2.metric("Live Longitude", f"{lon_deg:.4f}°")
                c3.metric("Current Time (UTC)", now.strftime('%Y-%m-%d %H:%M:%S'))
                
                # Step 4: Map Visual Rendering
                world = load_world_map()
                
                fig, ax = plt.subplots(figsize=(14, 7))
                world.plot(ax=ax, color='#eaeaea', edgecolor='white')
                
                # Draw target marker
                ax.scatter(lon_deg, lat_deg, color='#e63946', marker='X', s=300, 
                           edgecolor='black', linewidth=1.5, label=sat_name)
                
                ax.set_xlim([-180, 180])
                ax.set_ylim([-90, 90])
                ax.grid(True, linestyle=':', color='gray', alpha=0.5)
                ax.legend(loc='lower left', fontsize=12)
                
                st.pyplot(fig)
                
                # Refresh Trigger
                if st.button("🔄 Force Live Refresh Update", use_container_width=True):
                    st.rerun()
                    
            else:
                st.error(f"SGP4 Math Error (Code {error_code}).")
                
        except Exception as e:
            st.error(f"Processing Error: {e}")
    else:
        st.error(f"Could not fetch TLE data for NORAD ID: {search_query}")
        st.info("💡 Try using a common 5-digit ID: ISS (25544), Hubble (20580), NOAA 19 (33591)")
