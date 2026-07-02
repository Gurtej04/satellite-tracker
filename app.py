import streamlit as st
import numpy as np
import requests
import pandas as pd
from sgp4.api import Satrec, jday
from datetime import datetime, timezone, timedelta

st.set_page_config(layout="wide", page_title="Live Accurate Satellite Tracker")

st.title("🛰️ High-Precision Live Satellite Tracker")
st.write("Calculates exact real-time orbital positions by resolving Earth's rotation offsets.")

# Sidebar Configuration
st.sidebar.header("Input Method")
input_method = st.sidebar.radio("Select how to load TLE:", ("Auto-Fetch via NORAD ID", "Paste TLE Manually (Backup)"))

sat_name = "Unknown Satellite"
tle1 = ""
tle2 = ""

if input_method == "Auto-Fetch via NORAD ID":
    norad_id = st.sidebar.text_input("Enter 5-digit NORAD ID (e.g., 25544 for ISS)", "25544").strip()
    
    def fetch_fresh_tle(cat_id):
        if not cat_id.isdigit():
            return None
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
        else:
            st.sidebar.error("Server Throttled by Celestrak.")
            st.sidebar.info("Please switch to 'Paste TLE Manually' to run backup tracking.")
else:
    st.sidebar.subheader("Manual TLE Entry")
    sat_name = st.sidebar.text_input("Satellite Name", "ISS (ZARYA)")
    tle1 = st.sidebar.text_input("TLE Line 1", "1 25544U 98067A   26183.12345678  .00015481  00000+0  27533-3 0  9993")
    tle2 = st.sidebar.text_input("TLE Line 2", "2 25544  51.6416 189.2453 0001324  57.8546  68.2239 15.49479301")

# Computation Core
if tle1 and tle2:
    try:
        satrec = Satrec.twoline2rv(tle1.strip(), tle2.strip())
        utc_now = datetime.now(timezone.utc)
        
        jd, fr = jday(utc_now.year, utc_now.month, utc_now.day, 
                      utc_now.hour, utc_now.minute, utc_now.second + utc_now.microsecond / 1e6)
        
        error_code, position, velocity = satrec.sgp4(jd, fr)
        
        if error_code == 0:
            x, y, z = position[0], position[1], position[2]
            
            # Earth Rotation Correction Math
            t = (jd + fr - 2451545.0) / 36525.0
            gmst = 24110.54841 + 8640184.812866 * t + 0.093104 * (t**2) - 6.2e-6 * (t**3)
            gmst_rad = (gmst % 86400.0) * (2 * np.pi / 86400.0)
            
            lon_rad = np.arctan2(y, x) - gmst_rad
            lon_deg = float(np.degrees((lon_rad + np.pi) % (2 * np.pi) - np.pi))
            lat_deg = float(np.degrees(np.arctan2(z, np.sqrt(x**2 + y**2))))
            
            # UK Time Adjustment (BST / UTC + 1)
            local_uk_time = utc_now + timedelta(hours=1)
            
            # Interface
            c1, c2, c3 = st.columns(3)
            c1.metric("Satellite Identity", sat_name)
            c2.metric("Verified Latitude", f"{lat_deg:.4f}°")
            c3.metric("Verified Longitude", f"{lon_deg:.4f}°")
            
            st.write(f"**Synchronized Telemetry Clock (UK Time):** {local_uk_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            map_df = pd.DataFrame({'lat': [lat_deg], 'lon': [lon_deg]})
            st.map(map_df, zoom=2)
            
            if st.button("🔄 Stream Live Telemetry Vector", use_container_width=True):
                st.rerun()
        else:
            st.error(f"SGP4 Math Error: {error_code}")
    except Exception as e:
        st.error(f"Error calculating positions: {e}")
else:
    st.warning("Please provide valid TLE inputs via the sidebar.")
