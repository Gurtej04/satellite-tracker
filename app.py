import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
import requests
from sgp4.api import Satrec, jday
from datetime import datetime, timezone

st.set_page_config(layout="wide", page_title="Live Satellite Tracker")

st.title("🛰️ Universal Live Satellite Tracker")
st.write("Enter a satellite name to fetch its latest real-time TLE data and track its current position.")

# Sidebar Configuration
st.sidebar.header("Satellite Search")
search_query = st.sidebar.text_input("Enter Satellite Name (e.g., ISS, NOAA 19, HUBBLE)", "ISS (ZARYA)")

# Step 1: Fetch Live TLE data from Celestrak API
@st.cache_data(ttl=3600)  # Cache the TLE data for 1 hour so it's fast but stays updated
def fetch_live_tle(name):
    try:
        url = f"https://celestrak.org/NORAD/elements/gp.php?NAME={name}&FORMAT=tle"
        response = requests.get(url)
        if response.status_code == 200 and response.text.strip() and not "No data found" in response.text:
            lines = response.text.splitlines()
            if len(lines) >= 3:
                return lines[0].strip(), lines[1].strip(), lines[2].strip()
    except Exception:
        return None
    return None

tle_data = fetch_live_tle(search_query)

if tle_data:
    sat_name, tle_line1, tle_line2 = tle_data
    
    st.sidebar.success(f"Found live TLE data for: {sat_name}")
    st.sidebar.text(f"Line 1: {tle_line1}")
    st.sidebar.text(f"Line 2: {tle_line2}")
    
    try:
        # Step 2: Initialize SGP4 with fresh TLE
        satrec = Satrec.twoline2rv(tle_line1, tle_line2)
        
        # Step 3: Get the exact current live UTC time
        now = datetime.now(timezone.utc)
        jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond / 1e6)
        
        # Propagate
        error_code, position, velocity = satrec.sgp4(jd, fr)
        
        if error_code == 0:
            # Step 4: Convert Cartesian to Lat/Lon
            x, y, z = position[0], position[1], position[2]
            lon_deg = np.degrees(np.arctan2(y, x))
            lat_deg = np.degrees(np.arctan2(z, np.sqrt(x**2 + y**2)))
            
            # Display real-time data metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("Live Latitude", f"{lat_deg:.4f}°")
            c2.metric("Live Longitude", f"{lon_deg:.4f}°")
            c3.metric("Current Time (UTC)", now.strftime('%Y-%m-%d %H:%M:%S'))
            
            # Step 5: Render World Map
            world_url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_land.geojson"
            world = gpd.read_file(world_url)
            
            fig, ax = plt.subplots(figsize=(14, 7))
            world.plot(ax=ax, color='#eaeaea', edgecolor='white')
            
            # Plot the marker
            ax.scatter(lon_deg, lat_deg, color='#e63946', marker='X', s=300, 
                       edgecolor='black', linewidth=1.5, label=sat_name)
            
            ax.set_xlim([-180, 180])
            ax.set_ylim([-90, 90])
            ax.grid(True, linestyle=':', color='gray', alpha=0.5)
            ax.legend(loc='lower left', fontsize=12)
            st.pyplot(fig)
            
            # Auto-refresh button
            if st.button("🔄 Refresh Position Live"):
                st.rerun()
                
        else:
            st.error(f"SGP4 Propagation Error (Code {error_code}).")
            
    except Exception as e:
        st.error(f"Error executing tracking models: {e}")
else:
    st.error(f"Could not find a live satellite matching '{search_query}' on Celestrak. Please double check the spelling.")
