import streamlit as st
import numpy as np
import requests
import pandas as pd
from sgp4.api import Satrec, jday
from datetime import datetime, timezone, timedelta

st.set_page_config(layout="wide", page_title="Live Accurate Satellite Tracker")

st.title("🛰️ High-Precision Live Satellite Tracker")
st.write("Calculates exact real-time orbital positions by resolving Earth's rotation offsets.")

# Sidebar - Choice of entry method
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
            st.sidebar.error("Server Throttling Active: Celestrak blocked
