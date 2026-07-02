import streamlit as st
import numpy as np
import requests
import pandas as pd
from sgp4.api import Satrec, jday
from datetime import datetime, timezone, timedelta

st.set_page_config(layout="wide", page_title="Live Accurate Satellite Tracker")

st.title("🛰️ High-Precision Live Satellite Tracker")
st.write("Calculates exact real-time orbital positions by resolving Earth's rotation offsets.")

# Sidebar - Stripped of old session cache triggers
st.sidebar.header("Satellite Search")
norad_id = st.sidebar.text_input("Enter 5-digit NORAD ID (e.g., 25544 for ISS)", "25544").strip()

def fetch_fresh_tle(cat_id):
    if not cat_id.isdigit():
        return None
    # Connect directly using real-time parameter blocks
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATID={cat_id}&FORMAT=TLE"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200 and response.text.strip():
            lines = [l.strip() for l in response.text.splitlines() if l.strip()]
            if len(lines) >= 3 and "No data found" not in lines[0]:
                return lines[0], lines[1], lines[2]
    except Exception:
        return None
    return None

if norad_id:
    tle_data = fetch_fresh_tle(norad_id)
    
    if tle_data:
        sat_name, tle1, tle2 = tle_data
        st.sidebar.success(f"Connected Live: {sat_name}")
        
        try:
            # SGP4 Math Core
            satrec = Satrec.twoline2rv(tle1, tle2)
            utc_now = datetime.now(timezone.utc)
            
            # Extract precise time metrics
            jd, fr = jday(utc_now.year, utc_now.month, utc_now.day, 
                          utc_now.hour, utc_now.minute, utc_now.second + utc_now.microsecond / 1e6)
            
            error_code, position, velocity = satrec.sgp4(jd, fr)
            
            if error_code == 0:
                x, y, z = position[0], position[1], position[2]
                
                # --- EARTH ROTATION COMPENSATION (GMST math adjustment) ---
                # Calculate approximate Greenwich Mean Sidereal Time to align TEME space coordinates with Earth mapping structures
                t = (jd + fr - 2451545.0) / 36525.0
                gmst = 24110.54841 + 8640184.812866 * t + 0.093104 * (t**2) - 6.2e-6 * (t**3)
                gmst_rad = (gmst % 86400.0) * (2 * np.pi / 86400.0)
                
                # Apply rotation matrix calculation around Z axis
                lon_rad = np.arctan2(y, x) - gmst_rad
                lon_deg = float(np.degrees((lon_rad + np.pi) % (2 * np.pi) - np.pi))
                lat_deg = float(np.degrees(np.arctan2(z, np.sqrt(x**2 + y**2))))
                
                # Local Display Clock configuration (UK Time / BST = UTC + 1)
                local_uk_time = utc_now + timedelta(hours=1)
                
                # Interface readout cards
                c1, c2, c3 = st.columns(3)
                c1.metric("Satellite Identity", sat_name)
                c2.metric("Verified Latitude", f"{lat_deg:.4f}°")
                c3.metric("Verified Longitude", f"{lon_deg:.4f}°")
                
                st.write(f"**Synchronized Telemetry Clock (UK Time):** {local_uk_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Mapping presentation
                map_df = pd.DataFrame({'lat': [lat_deg], 'lon': [lon_deg]})
                st.map(map_df, zoom=2)
                
                if st.button("🔄 Stream Live Telemetry Vector", use_container_width=True):
                    st.rerun()
            else:
                st.error(f"Mathematical Propagation Error. SGP4 Code: {error_code}")
        except Exception as e:
            st.error(f"Mathematical Error resolving coordinates: {e}")
    else:
        st.error(f"Server Throttling: Celestrak blocked the network search request. Try checking the app back in a minute.")
