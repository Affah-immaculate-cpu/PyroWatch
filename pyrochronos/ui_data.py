"""
The "📥 Data" tab: get real FIRMS data into the app.

Three ways in:
  1. Upload CSVs you downloaded from the FIRMS website.
  2. Fetch directly from the FIRMS API with your MAP_KEY.
  3. (Command line) python scripts/fetch_firms.py  — see README.

Kept separate from app.py so app.py stays readable.
"""

from datetime import date, timedelta
from pathlib import PureWindowsPath

import pandas as pd
import streamlit as st

from pyro import firms_api
from pyro.processing import DEMO_BACKUP_DIR, RAW_DIR, list_raw_files, move_demo_files, sensor_of_csv


def _get_saved_key() -> str | None:
    """Read FIRMS_MAP_KEY from .streamlit/secrets.toml if it exists."""
    try:
        return st.secrets.get("FIRMS_MAP_KEY")
    except Exception:  # no secrets file at all
        return None


def _refresh():
    """Redraw the app. load_data() notices the changed files by itself."""
    st.rerun()


def render_data_manager():
    st.subheader("Files the dashboard is using")
    files = list_raw_files()
    if files.empty:
        st.info("No CSV files in `data/raw/` yet. Upload or fetch some below.")
    else:
        st.dataframe(files.drop(columns="modified"), width="stretch", hide_index=True)

    has_demo = bool(files["demo"].any()) if not files.empty else False
    has_real = bool((~files["demo"]).any()) if not files.empty else False
    if has_demo and has_real:
        st.error("You're mixing **synthetic demo data** with real data. "
                 "Remove the demo files before presenting results.", icon="🚫")

    c1, c2 = st.columns(2)
    if has_demo and c1.button("🧹 Remove demo data", help="Moves demo CSVs to data/demo_backup/"):
        n = move_demo_files(to_backup=True)
        st.toast(f"Moved {n} demo file(s) to data/demo_backup/")
        _refresh()
    backup_exists = any(DEMO_BACKUP_DIR.glob("*/*.csv"))
    if not has_demo and backup_exists and c2.button("↩️ Restore demo data"):
        n = move_demo_files(to_backup=False)
        st.toast(f"Restored {n} demo file(s)")
        _refresh()

    st.divider()

    # ------------------------------------------------------------------ upload
    st.subheader("Option 1 · Upload FIRMS CSV files")
    st.caption("From firms.modaps.eosdis.nasa.gov → *Archive Download* (good for whole "
               "seasons). Unzip and upload the CSVs here. MODIS vs VIIRS is detected "
               "from the columns.")
    uploads = st.file_uploader("FIRMS CSVs", type="csv", accept_multiple_files=True)
    if uploads and st.button("💾 Save uploaded files"):
        saved = []
        for up in uploads:
            filename = PureWindowsPath(up.name).name
            if filename in {"", ".", ".."}:
                st.error(f"`{up.name}`: invalid filename. Skipped.")
                continue
            df = pd.read_csv(up)
            sensor = sensor_of_csv(df.columns)
            if sensor is None:
                st.error(f"`{up.name}`: doesn't look like a FIRMS file "
                         "(no `brightness` or `bright_ti4` column). Skipped.")
                continue
            folder = RAW_DIR / sensor.lower()
            folder.mkdir(parents=True, exist_ok=True)
            df.to_csv(folder / filename, index=False)
            saved.append(f"{filename} → {sensor} ({len(df):,} rows)")
        if saved:
            st.success("Saved:\n\n- " + "\n- ".join(saved))
            st.button("🔄 Reload dashboard with new data", key="reload_upload")

    st.divider()

    # --------------------------------------------------------------- API fetch
    st.subheader("Option 2 · Fetch from the FIRMS API")
    saved_key = _get_saved_key()
    if saved_key:
        st.caption("✅ Using the MAP_KEY from `.streamlit/secrets.toml`.")
        map_key = saved_key
    else:
        map_key = st.text_input(
            "FIRMS MAP_KEY", type="password",
            help="Free from firms.modaps.eosdis.nasa.gov/api/map_key/. "
                 "To avoid typing it every time, put it in .streamlit/secrets.toml "
                 "(see README). It is never written to disk by this app.")

    col_a, col_b = st.columns(2)
    with col_a:
        area_name = st.selectbox("Area", list(firms_api.AREAS) + ["Custom box"])
        if area_name == "Custom box":
            w, s_, e, n = st.columns(4)
            bbox = (w.number_input("West", value=-3.3), s_.number_input("South", value=4.6),
                    e.number_input("East", value=1.3), n.number_input("North", value=11.2))
        else:
            bbox = firms_api.AREAS[area_name]
            st.caption(f"Box (W, S, E, N): {bbox}")
        sources = st.multiselect(
            "Sources", list(firms_api.SOURCES),
            default=["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "MODIS_NRT"],
            help="NRT = recent weeks/months. SP = older, final archive. "
                 "Use 'Check what dates are available' to see each source's range.")
    with col_b:
        today = date.today()
        start = st.date_input("Start date", value=today - timedelta(days=14))
        end = st.date_input("End date", value=today - timedelta(days=1))
        n_days = (end - start).days + 1 if end >= start else 0
        calls = len(sources) * -(-n_days // firms_api.MAX_DAYS_PER_REQUEST)
        st.caption(f"{n_days} days × {len(sources)} source(s) ≈ {calls} API calls. "
                   "Each day counts against your key's limit (resets every 10 minutes).")

    b1, b2, b3 = st.columns(3)
    if b1.button("🔑 Check key", disabled=not map_key):
        try:
            st.json(firms_api.check_key(map_key))
        except Exception as err:
            st.error(f"Couldn't check key: {err}")
    if b2.button("📆 Check what dates are available", disabled=not map_key):
        try:
            st.dataframe(firms_api.data_availability(map_key), hide_index=True)
        except Exception as err:
            st.error(f"Couldn't get availability: {err}")

    if b3.button("⬇️ Fetch data", type="primary", disabled=not (map_key and sources and n_days)):
        progress = st.progress(0.0, text="Starting…")
        total_saved = 0
        for i, source in enumerate(sources):
            def on_progress(done, total, i=i, source=source):
                frac = (i + done / total) / len(sources)
                progress.progress(frac, text=f"{source}: {done}/{total} days")
            try:
                df = firms_api.fetch_range(map_key, source, bbox, start, end, on_progress)
            except firms_api.FirmsError as err:
                st.error(f"**{source}**: FIRMS said: {err}")
                continue
            except Exception as err:
                st.error(f"**{source}**: request failed ({err}). Check your internet connection.")
                continue
            if df.empty or len(df.columns) <= 1:
                st.warning(f"{source}: no detections in this area/date range.")
                continue
            folder = RAW_DIR / firms_api.SOURCES[source].lower()
            folder.mkdir(parents=True, exist_ok=True)
            name = firms_api.output_filename(source, bbox, start, end)
            df.to_csv(folder / name, index=False)
            total_saved += len(df)
            st.success(f"{source}: saved {len(df):,} detections → `{folder.name}/{name}`")
        progress.progress(1.0, text="Done")
        if total_saved:
            st.button("🔄 Reload dashboard with new data", key="reload_fetch")
