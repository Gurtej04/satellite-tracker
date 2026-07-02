import streamlit as st
import numpy as np
import requests
import pandas as pd
from sgp4.api import Satrec, jday
from datetime import datetime, timezone

st.set_page_config(layout="wide", page_title="Live Satellite Tracker (GMT)")

st.title("🛰️ Universal Live Satellite Tracker")
st.write("Track any active satellite by trying a live API pull, or paste the TLE text yourself below.")

# Layout Columns
col_input, col_display = st.columns([1, 2])

with col_input:
    st.header("1. Input Configuration")
    input_method = st.radio("Choose Input Method:", ("Fetch via NORAD ID", "Paste Raw TLE Text Manually"))
    
    tle_line1 = ""
    tle_line2 = ""
    sat_name = "Unknown Satellite"
    
    if input_method == "Fetch via NORAD ID":
        norad_id = st.text_input("Enter 5-digit NORAD ID (e.g., 25544 for ISS)", "25544").strip()
        
        if st.button("🛰️ Fetch Live TLE", use_container_width=True):
            if norad_id.isdigit():
                url = f"https://celestrak.org/NORAD/elements/gp.php?CATID={norad_id}&FORMAT=TLE"
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                    response = requests.get(url, headers=headers, timeout=8)
                    
                    if response.status_code == 200 and response.text.strip():
                        lines = [l.strip() for l in response.text.splitlines() if l.strip()]
                        if len(lines) >= 3 and "No data found" not in lines[0]:
                            st.session_state['sat_name'] = lines[0]
                            st.session_state['tle1'] = lines[1]
                            st.session_state['tle2'] = lines[2]
                            st.success(f"Successfully fetched: {lines[0]}")
                        else:
                            st.error("No active data found on Celestrak for this ID.")
                    else:
                        st.error(f"Celestrak responded with error code: {response.status_code}")
                except Exception as e:
                    st.error("Network connection blocked by cloud host firewall. Use manual paste method below!")
            else:
                st.warning("Please enter a valid numeric ID.")
                
        sat_name = st.session_state.get('sat_name', 'ISS (ZARYA)')
        tle_line1 = st.session_state.get('tle1', '1 25544U 98067A   24061.62141410  .00015481  00000+0  27533-3 0  9993')
        tle_line2 = st.session_state.get('tle2', '2 25544  51.6416 189.2453 0001324  57.8546  68.2239 15.49479301441113')

    else:
        st.info("💡 You can find fresh TLE entries directly on websites like celestrak.org")
        sat_name = st.text_input("Satellite Name Label", "Custom Target")
        tle_line1 = st.text_input("Line 1", "1 25544U 98067A   24061.62141410  .00015481  00000+0  27533-3 0  9993").strip()
        tle_line2 = st.text_input("Line 2", "2 25544  51.6416 189.2453 0001324  57.8546  68.2239 15.49479301441113").strip()

# Run the Tracking computations
with col_display:
    st.header("2. Live Tracking Status")
    
    if tle_line1 and tle_line2:
        try:
            satrec = Satrec.twoline2rv(tle_line1, tle_line2)
            
            # Enforce current system clock tracking explicitly tied to timezone-neutral GMT calculations
            now = datetime.now(timezone.utc)
            jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond / 1e6)
            
            error_code, position, velocity = satrec.sgp4(jd, fr)
            
            if error_code == 0:
                x, y, z = position[0], position[1], position[2]
                lon_deg = float(np.degrees(np.arctan2(y, x)))
                lat_deg = float(np.degrees(np.arctan2(z, np.sqrt(x**2 + y**2))))
                
                # Render clean metric readout updating the metrics card to explicit GMT
                m1, m2, m3 = st.columns(3)
                m1.metric("Target Label", sat_name)
                m2.metric("Calculated Latitude", f"{lat_deg:.4f}°")
                m3.metric("Calculated Longitude", f"{lon_deg:.4f}°")
                
                # Visual Time Stamp string converted to clear GMT naming conventions
                st.write(f"*Last Computed Position Epoch: {now.strftime('%Y-%m-%d %H:%M:%S')} GMT*")
                
                # Map rendering engine
                map_df = pd.DataFrame({'lat': [lat_deg], 'lon': [lon_deg]})
                st.map(map_df, zoom=1)
                
                if st.button("🔄 Force Live Coordinate Refresh", use_container_width=True):
                    st.rerun()
            else:
                st.error(f"SGP4 Math Error (Code {error_code}). The TLE structural formatting may be incorrect.")
        except Exception as e:
            st.error(f"Calculation Error: {e}")
