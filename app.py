
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
from sgp4.api import Satrec, jday
from datetime import datetime, timezone

st.set_page_config(layout="wide", page_title="Satellite TLE Tracker")

st.title("🛰️ Interactive Satellite TLE Tracker")
st.write("Modify the TLE inputs in the sidebar to track any satellite in real-time.")

# Sidebar setup
st.sidebar.header("Configuration")
satellite_name = st.sidebar.text_input("Satellite Name", "ISS (ZARYA)")
tle_line1 = st.sidebar.text_area("TLE Line 1", "1 25544U 98067A   24061.62141410  .00015481  00000+0  27533-3 0  9993", height=70)
tle_line2 = st.sidebar.text_area("TLE Line 2", "2 25544  51.6416 189.2453 0001324  57.8546  68.2239 15.49479301441113", height=70)

if st.sidebar.button("Update Map", use_container_width=True):
    try:
        # Strip trailing white spaces that break parsing
        l1 = tle_line1.strip()
        l2 = tle_line2.strip()
        
        # SGP4 Setup
        satrec = Satrec.twoline2rv(l1, l2)
        now = datetime.now(timezone.utc)
        jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond / 1e6)
        
        error_code, position, velocity = satrec.sgp4(jd, fr)
        
        if error_code == 0:
            # Lat/Lon Conversion
            x, y, z = position[0], position[1], position[2]
            lon_deg = np.degrees(np.arctan2(y, x))
            lat_deg = np.degrees(np.arctan2(z, np.sqrt(x**2 + y**2)))
            
            # Formatting layout metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("Latitude", f"{lat_deg:.4f}°")
            c2.metric("Longitude", f"{lon_deg:.4f}°")
            c3.metric("Calculation Time (UTC)", now.strftime('%Y-%m-%d %H:%M:%S'))
            
            # Map generation 
            world_url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_land.geojson"
            world = gpd.read_file(world_url)
            
            fig, ax = plt.subplots(figsize=(14, 7))
            world.plot(ax=ax, color='#eaeaea', edgecolor='white')
            
            # Visualizing target
            ax.scatter(lon_deg, lat_deg, color='#e63946', marker='X', s=300, 
                       edgecolor='black', linewidth=1.5, label=satellite_name)
            
            ax.set_xlim([-180, 180])
            ax.set_ylim([-90, 90])
            ax.grid(True, linestyle=':', color='gray', alpha=0.5)
            ax.legend(loc='lower left', fontsize=12)
            st.pyplot(fig)
        else:
            st.error(f"SGP4 Math Error (Code {error_code}). The orbital math could not resolve.")
            
    except Exception as e:
        st.error(f"Formatting Error: Please verify that lines are exactly standard TLE widths. Details: {e}")
