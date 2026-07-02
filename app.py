import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
import requests
from sgp4.api import Satrec, jday
from datetime import datetime, timezone

st.set_page_config(layout="wide", page_title="Live Satellite Tracker")

st.title("🛰️ Universal Live Satellite Tracker")
st.write("Enter a satellite's unique NORAD Catalog ID or its exact name to fetch live TLE tracking data.")

# Sidebar Configuration
st.sidebar.header("Satellite Search")
search_query = st.sidebar.text_input("Enter NORAD ID or Name (e.g., 25544, NOO-19, ISS)", "25544")

# Step 1: Upgraded Fetching function that handles IDs or Names
@st.cache_data(ttl=60)  # Short cache so it refreshes position often but doesn't spam the API
def fetch_live_tle(query):
    query = query.strip()
    if not query:
        return None
        
    # Check if user entered a 5-digit number (Catalog ID)
    if query.isdigit():
        url = f"https://celestrak.org/NORAD/elements/gp.php?CATID={query}&FORMAT=tle"
    else:
        # Otherwise treat it as a general text name query
        url = f"https://celestrak.org/NORAD/elements/gp.php?NAME={query}&FORMAT=tle"
        
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and response.text.strip():
            lines = response.text.splitlines()
            # A valid TLE response from Celestrak will have 3 lines per satellite
            if len(lines) >= 3 and not "No data found" in lines[0]:
                return lines[0].strip(), lines[1].strip(), lines[2].strip()
    except Exception:
        return None
    return None

tle_data = fetch_live_tle(search_query)

if tle_data:
    sat_name, tle_line1, tle_line2 = tle_data
    
    st.sidebar.success(f"🎯 Connected: {sat_name}")
    with st.sidebar.expander("View Raw TLE Data"):
        st.text(f"{sat_name}\n{tle_line1}\n{tle_line2}")
    
    try:
        # Step 2: Initialize SGP4
        satrec = Satrec.twoline2rv(tle_line1, tle_line2)
        
        # Step 3: Get exact live UTC time
        now = datetime.now(timezone.utc)
        jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond / 1e6)
        
        # Propagate position
        error_code, position, velocity = satrec.sgp4(jd, fr)
        
        if error_code == 0:
            # Step 4: Convert Cartesian to Lat/Lon
            x, y, z = position[0], position[1], position[2]
            lon_deg = np.degrees(np.arctan2(y, x))
            lat_deg = np.degrees(np.arctan2(z, np.sqrt(x**2 + y**2)))
            
            # Display tracking data metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("Live Latitude", f"{lat_deg:.4f}°")
            c2.metric("Live Longitude", f"{lon_deg:.4f}°")
            c3.metric("Current Time (UTC)", now.strftime('%Y-%m-%d %H:%M:%S'))
            
            # Step 5: Render World Map using online geojson
            world_url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_land.geojson"
            world = gpd.read_file(world_url)
            
            fig, ax = plt.subplots(figsize=(14, 7))
            world.plot(ax=ax, color='#eaeaea', edgecolor='white')
            
            # Draw the live position marker
            ax.scatter(lon_deg, lat_deg, color='#e63946', marker='X', s=300, 
                       edgecolor='black', linewidth=1.5, label=sat_name)
            
            ax.set_xlim([-180, 180])
            ax.set_ylim([-90, 90])
            ax.grid(True, linestyle=':', color='gray', alpha=0.5)
            ax.legend(loc='lower left', fontsize=12)
            st.pyplot(fig)
            
            # Live Auto-Refresh
            if st.button("🔄 Track Live Position", use_container_width=True):
                st.rerun()
                
        else:
            st.error(f"SGP4 Math Error (Code {error_code}).")
            
    except Exception as e:
        st.error(f"Error parsing tracking models: {e}")
else:
    st.error(f"Could not find any active satellite matching '{search_query}'.")
    st.info("💡 Pro-Tip: Try searching by its 5-digit NORAD ID number instead! For example:\n"
            "- ISS (International Space Station): `25544`\n"
            "- Hubble Space Telescope: `20580`\n"
            "- NOAA-19 Weather Satellite: `33591`")
