"""PyroChronos wildfire intelligence dashboard."""

from datetime import date, datetime, timedelta
from html import escape
import math
import re
from pathlib import Path

import folium
from folium.plugins import HeatMap, MarkerCluster
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from pyro import aoi, places
from pyro.firms_api import AREAS
from pyro.insights import build_alerts, calendar_matrix, daily_summary
from pyro.processing import (
    DEMO_PREFIX,
    data_fingerprint,
    harmonize,
    list_raw_files,
    load_raw_hotspots,
)
from utils.dashboard_theme import (
    PALETTE,
    inject_theme,
    render_hero,
    render_kpis,
    render_topbar,
    section_heading,
    style_chart,
)
from ui_data import render_data_manager


st.set_page_config(
    page_title="PyroChronos | Wildfire Intelligence Center",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_theme()

SENSOR_COLORS = {"MODIS": "#FFB547", "VIIRS": "#FF6B35"}
SEVERITY_COLORS = {
    "Critical": "#FF4545",
    "High": "#FF6B35",
    "Medium": "#FFB547",
    "Low": "#60A5FA",
}
SEVERITY_ORDER = ["Critical", "High", "Medium", "Low"]
CONFIDENCE_ORDER = ["low", "nominal", "high", "unknown"]
# Sidebar pages and their Material icons (Streamlit-native `:material/…:` icons).
PAGE_OVERVIEW = "Overview"
PAGE_MAP = "Fire Detection Map"
PAGE_ANALYTICS = "Analytics & Insights"
PAGE_ALERTS = "Emberwatch Alerts"
PAGE_DATA = "Data Explorer"
PAGE_SETTINGS = "Settings & Methodology"
NAV_ITEMS = {
    PAGE_OVERVIEW: ":material/space_dashboard:",
    PAGE_MAP: ":material/map:",
    PAGE_ANALYTICS: ":material/insights:",
    PAGE_ALERTS: ":material/local_fire_department:",
    PAGE_DATA: ":material/table_view:",
    PAGE_SETTINGS: ":material/tune:",
}
# Old page names (kept in a browser session) -> where that content lives now.
LEGACY_PAGES = {
    "Historical Analysis": PAGE_ANALYTICS,
    "Alert Management": PAGE_ALERTS,
    "System Information": PAGE_SETTINGS,
}


def go_to(page: str) -> None:
    """Button callback: switch page before the rerun, so the highlight is instant."""
    st.session_state["dashboard_page"] = page


@st.cache_data(show_spinner="Reading and harmonizing FIRMS observations…")
def load_data(max_km: float, max_hours: float, files: tuple):
    raw = load_raw_hotspots()
    return harmonize(raw, max_km=max_km, max_hours=max_hours)


@st.cache_data(show_spinner="Reading Ghana administrative boundaries…")
def load_boundary(path: str, modified: float):
    return aoi.load_boundary(path)


def severity_for_frp(value: float, threshold: float) -> str:
    if pd.isna(value):
        return "Low"
    if value >= max(2 * threshold, 200):
        return "Critical"
    if value >= threshold:
        return "High"
    if value >= threshold / 2:
        return "Medium"
    return "Low"


def add_aoi_outline(map_object, geometry) -> None:
    folium.GeoJson(
        aoi.to_geojson(geometry),
        name="Ghana boundary",
        style_function=lambda _: {
            "color": "#FFB547",
            "weight": 2,
            "opacity": 0.9,
            "fill": False,
            "dashArray": "5 5",
        },
    ).add_to(map_object)


def render_map_legend() -> None:
    items = "".join(
        f'<span class="pc-legend-item"><i class="pc-legend-dot" '
        f'style="--legend-color:{color}"></i>{label}</span>'
        for label, color in SEVERITY_COLORS.items()
    )
    st.markdown(f'<div class="pc-map-legend">{items}</div>', unsafe_allow_html=True)


def render_fire_map(
    detections: pd.DataFrame,
    groups: pd.DataFrame,
    geometry,
    *,
    height: int = 550,
    basemap: str = "Dark intelligence",
    show_heatmap: bool = True,
    key: str = "fire_map",
    before_legend=None,
) -> None:
    """`before_legend`: optional function drawn between the map and its severity legend."""
    if detections.empty:
        st.info("No detections match the selected filters and date range.")
        return

    center_lat, center_lon = geometry.centroid.y, geometry.centroid.x
    fire_map = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=7,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
    )
    tile_layers = {
        # CARTO's dark tiles now need an API key (they show "API KEY REQUIRED"),
        # so the dark style uses Esri's free dark grey canvas instead.
        "Dark intelligence": (
            "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
            "Dark intelligence",
            "Tiles &copy; Esri",
        ),
        "Satellite imagery": (
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            "Esri satellite imagery",
            "Tiles &copy; Esri",
        ),
        "Terrain": (
            "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
            "OpenTopoMap terrain",
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        ),
        "Light reference": (
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            "OpenStreetMap",
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        ),
    }
    tiles, layer_name, attribution = tile_layers[basemap]
    folium.TileLayer(tiles=tiles, name=layer_name, attr=attribution, show=True).add_to(fire_map)
    if basemap == "Dark intelligence":  # place names on top of the dark canvas
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
            name="Place names", attr="Tiles &copy; Esri", overlay=True, control=False,
        ).add_to(fire_map)
    add_aoi_outline(fire_map, geometry)

    if show_heatmap:
        HeatMap(
            detections[["latitude", "longitude"]].values.tolist(),
            name="Detection density",
            radius=16,
            blur=20,
            min_opacity=0.28,
            gradient={
                0.25: "#60A5FA",
                0.55: "#FFB547",
                0.8: "#FF6B35",
                1.0: "#FF4545",
            },
        ).add_to(fire_map)

    marker_layer = MarkerCluster(
        name="Clustered fire observations",
        options={
            "maxClusterRadius": 38,
            "showCoverageOnHover": False,
            "spiderfyOnMaxZoom": True,
            "disableClusteringAtZoom": 11,
        },
        icon_create_function="""
        function(cluster) {
            var count = cluster.getChildCount();
            var size = count >= 100 ? 46 : (count >= 25 ? 40 : 34);
            return L.divIcon({
                html: '<div style="width:' + size + 'px;height:' + size +
                  'px;border-radius:50%;display:grid;place-items:center;color:#fff;' +
                  'font-weight:700;font-size:12px;background:rgba(255,107,53,.86);' +
                  'border:2px solid rgba(255,181,71,.85);box-shadow:0 0 16px rgba(255,107,53,.38)">' +
                  count + '</div>',
                className: 'pc-cluster-icon',
                iconSize: L.point(size, size)
            });
        }
        """,
    ).add_to(fire_map)

    detections_layer = groups if not groups.empty else detections
    is_grouped = not groups.empty
    max_markers = 12000
    shown = detections_layer.head(max_markers)
    for row in shown.itertuples(index=False):
        frp = float(row.max_frp if is_grouped else row.frp)
        severity = severity_for_frp(frp, st.session_state.get("alert_frp_threshold", 100.0))
        color = SEVERITY_COLORS[severity]
        if is_grouped:
            sensor = row.sensors
            timestamp = pd.Timestamp(row.first_seen).strftime("%d %b %Y · %H:%M UTC")
            details = (
                f"<b>{escape(severity)} intensity incident</b><br>"
                f"{escape(str(sensor))} · {int(row.n_detections)} detections<br>"
                f"First observed: {timestamp}<br>"
                f"Peak FRP: {frp:.1f} MW<br>"
                f"Duration: {row.duration_hours:.1f} hours"
            )
            point_lat, point_lon = row.latitude, row.longitude
            radius = min(9, 4 + math.sqrt(int(row.n_detections)))
        else:
            sensor = row.sensor
            timestamp = pd.Timestamp(row.datetime_utc).strftime("%d %b %Y · %H:%M UTC")
            details = (
                f"<b>{escape(severity)} intensity detection</b><br>"
                f"{escape(str(sensor))} · {escape(str(row.satellite))}<br>"
                f"Observed: {timestamp}<br>"
                f"Confidence: {escape(str(row.confidence_class)).title()}<br>"
                f"FRP: {frp:.1f} MW"
            )
            point_lat, point_lon = row.latitude, row.longitude
            radius = 5
        folium.CircleMarker(
            location=[point_lat, point_lon],
            radius=radius,
            color="#F1F5F9",
            weight=1,
            fill=True,
            fill_color=color,
            fill_opacity=0.88,
            tooltip=f"{severity} · {escape(str(sensor))} · {frp:.1f} MW",
            popup=folium.Popup(details, max_width=280),
        ).add_to(marker_layer)

    bounds = geometry.bounds
    fire_map.fit_bounds(
        [[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
        padding=(18, 18),
    )
    folium.LayerControl(position="topright", collapsed=True).add_to(fire_map)
    st_folium(
        fire_map,
        height=height,
        use_container_width=True,
        returned_objects=[],
        key=key,
    )
    if len(detections_layer) > max_markers:
        st.caption(f"Showing {max_markers:,} of {len(detections_layer):,} mapped records.")
    if before_legend is not None:
        before_legend()
    render_map_legend()
    st.caption(
        "FRP severity is a display classification, not a fire-behavior forecast. "
        "FIRMS detections indicate thermal anomalies, not confirmed incident perimeters."
    )


def section_page(title: str, subtitle: str, eyebrow: str) -> None:
    render_hero(title, subtitle, eyebrow)


@st.cache_data(show_spinner=False)
def ghana_places() -> pd.DataFrame:
    return places.load_places()


def make_alert_table(
    alerts: pd.DataFrame,
    raw: pd.DataFrame,
    groups: pd.DataFrame,
    region_shapes: list,
    region_names: list,
    frp_threshold: float,
) -> pd.DataFrame:
    if alerts.empty:
        return pd.DataFrame(
            columns=["ID", "Severity", "Location", "Detection time", "Confidence",
                     "FRP (MW)", "Alert", "Status"]
        )

    confidence_by_group = (
        raw.groupby("group_id")["confidence_class"]
        .agg(lambda values: values.mode().iloc[0] if not values.mode().empty else "unknown")
        .to_dict()
    )
    groups_by_id = groups.set_index("group_id", drop=False) if not groups.empty else pd.DataFrame()
    statuses = st.session_state.setdefault("alert_statuses", {})
    records = []
    for alert in alerts.itertuples(index=False):
        message = str(alert.message)
        match = re.search(r"Group #(\d+)", message)
        group_id = int(match.group(1)) if match else None
        group = groups_by_id.loc[group_id] if group_id is not None and group_id in groups_by_id.index else None
        frp = float(group["max_frp"]) if group is not None else np.nan
        severity = severity_for_frp(frp, frp_threshold) if alert.level == "high" else (
            "Medium" if alert.level == "warning" else "Low"
        )
        location = "Ghana"
        if pd.notna(alert.latitude) and pd.notna(alert.longitude):
            point_frame = pd.DataFrame({"latitude": [alert.latitude], "longitude": [alert.longitude]})
            for name, shape in zip(region_names, region_shapes):
                if bool(aoi.inside(point_frame, shape).iloc[0]):
                    location = name
                    break
        if pd.notna(alert.latitude) and pd.notna(alert.longitude):
            # Town names make alerts searchable ("Tamale", "Bolgatanga", …).
            town = places.describe(ghana_places(), alert.latitude, alert.longitude)
            location = " · ".join(
                part for part in (location, town, f"{alert.latitude:.3f}, {alert.longitude:.3f}")
                if part
            )
        alert_id = f"{alert.date}|{alert.rule}|{group_id}|{alert.latitude}|{alert.longitude}"
        records.append({
            "ID": alert_id,
            "Severity": severity,
            "Location": location,
            "Detection time": pd.Timestamp(alert.date).strftime("%d %b %Y"),
            "Confidence": confidence_by_group.get(group_id, "—"),
            "FRP (MW)": frp,
            "Alert": f"{alert.rule} — {message}",
            "Status": statuses.get(alert_id, "New"),
        })
    return pd.DataFrame(records)


def render_alerts(
    daily: pd.DataFrame,
    raw: pd.DataFrame,
    groups: pd.DataFrame,
    region_shapes: list,
    region_names: list,
    spike_sigma: float,
    frp_threshold: float,
    selected_severities: list[str],
) -> pd.DataFrame:
    alerts = build_alerts(daily, groups, spike_sigma=spike_sigma, frp_threshold=frp_threshold)
    table = make_alert_table(alerts, raw, groups, region_shapes, region_names, frp_threshold)
    if table.empty:
        st.info("No alert rules match the current filters.")
        return table

    visible = table[table["Severity"].isin(selected_severities)].copy()
    search = st.text_input("Search alerts",
                           placeholder="Search town, region, sensor, rule or date… e.g. Tamale")
    if search.strip():
        searchable = visible.astype(str).apply(lambda column: column.str.contains(
            search.strip(), case=False, na=False
        ))
        visible = visible[searchable.any(axis=1)]

    counts = table["Severity"].value_counts()
    cards = [
        {"label": f"{severity} alerts", "value": f"{int(counts.get(severity, 0)):,}",
         "detail": "Current rule matches", "accent": color}
        for severity, color in [
            ("Critical", SEVERITY_COLORS["Critical"]),
            ("High", SEVERITY_COLORS["High"]),
            ("Medium", SEVERITY_COLORS["Medium"]),
            ("Low", SEVERITY_COLORS["Low"]),
        ]
    ]
    render_kpis(cards)

    if visible.empty:
        if search.strip():
            # Say where the alerts actually are, so an empty result isn't a dead end.
            towns = sorted({
                part.removeprefix("near ").split(" (")[0]
                for location in table["Location"]
                for part in location.split(" · ")
                if part.startswith("near ")
            })
            st.info(
                f"No alerts mention “{search.strip()}”. There are {len(table):,} alerts for the "
                "current filters" + (f", located near: {', '.join(towns)}." if towns else ".")
                + " Widen the date range or lower the FRP threshold to see more."
            )
        else:
            st.info("No alerts match the selected severities.")
        return table

    section_heading("Alert queue", f"{len(visible):,} visible · status is saved for this session")
    editable = visible.drop(columns="ID").reset_index(drop=True)
    edited = st.data_editor(
        editable,
        width="stretch",
        hide_index=True,
        disabled=[column for column in editable.columns if column != "Status"],
        column_config={
            "Severity": st.column_config.TextColumn("Severity", help="Rule-derived severity."),
            "FRP (MW)": st.column_config.NumberColumn("FRP (MW)", format="%.1f"),
            "Status": st.column_config.SelectboxColumn(
                "Status", options=["New", "Acknowledged", "Resolved"], required=True
            ),
        },
        key="alert_queue_editor",
    )
    for alert_id, status in zip(visible["ID"], edited["Status"]):
        st.session_state["alert_statuses"][alert_id] = status
    st.caption(
        "Rule-based summaries only—not emergency warnings or push notifications. "
        "Acknowledgement state is local to this browser session."
    )
    return table


def render_overview(
    raw: pd.DataFrame,
    groups: pd.DataFrame,
    daily: pd.DataFrame,
    geometry,
    alert_rows: pd.DataFrame,
    high_threshold: float,
    period_label: str,
) -> None:
    section_page(
        "Wildfire Intelligence Center",
        "Real-time wildfire monitoring, geospatial intelligence and environmental risk analytics.",
        "Ghana · Operational picture",
    )
    if raw["source_file"].str.startswith(DEMO_PREFIX).any():
        st.warning(
            "Synthetic demonstration detections are present. They are not satellite observations.",
            icon="⚠️",
        )
    last_seen = pd.Timestamp(raw["datetime_utc"].max())
    recent_window_start = last_seen - pd.Timedelta(hours=24)
    recent_incidents = int((groups["last_seen"] >= recent_window_start).sum()) if not groups.empty else 0
    high_risk = int((groups["max_frp"] >= high_threshold).sum()) if not groups.empty else 0
    render_kpis([
        {"label": "Total Fire Detections", "value": f"{len(raw):,}",
         "detail": period_label, "accent": "#FF6B35"},
        {"label": "Recent Fire Incidents", "value": f"{recent_incidents:,}",
         "detail": "Within 24h of latest observed record", "accent": "#FFB547"},
        {"label": "High-Risk Locations", "value": f"{high_risk:,}",
         "detail": f"Incident FRP ≥ {high_threshold:.0f} MW", "accent": "#FF4545"},
        {"label": "Last Detection", "value": last_seen.strftime("%d %b"),
         "detail": last_seen.strftime("%Y · %H:%M UTC"), "accent": "#22C55E"},
    ])

    def priority_signals() -> None:
        section_heading("Priority signals", "Derived from active alert rules")
        if alert_rows.empty:
            st.markdown('<div class="pc-panel pc-muted">No alert signals match this period.</div>',
                        unsafe_allow_html=True)
            return
        for _, alert in alert_rows.head(4).iterrows():
            severity = alert["Severity"]
            color = SEVERITY_COLORS[severity]
            st.markdown(
                f"""
                <div class="pc-alert-row" style="--alert-color:{color}">
                  <div class="pc-alert-title">{escape(severity)} · {escape(alert['Alert'].split(' — ')[0])}</div>
                  <div class="pc-alert-copy">{escape(alert['Location'])} · {escape(alert['Detection time'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        # Switch page in a callback so the sidebar highlight updates on the same click.
        st.button(
            f"Open {PAGE_ALERTS} →",
            key="overview_open_alerts",
            help="Search, filter and update alert status for this session.",
            on_click=go_to,
            args=(PAGE_ALERTS,),
        )

    section_heading("Geospatial fire activity", "Clustered detections · severity-colored markers")
    left, right = st.columns([1.62, 1], gap="medium")
    with left:
        # Priority signals sit under the map, just above the severity legend.
        render_fire_map(raw, groups, geometry, height=500, key="overview_fire_map",
                        before_legend=priority_signals)
    with right:
        section_heading("Detection trend", "Daily observations in selected period")
        if daily.empty:
            st.info("No daily detections available.")
        else:
            trend = daily.melt(
                id_vars="date",
                value_vars=[column for column in daily if column.endswith("_detections")],
                var_name="sensor",
                value_name="sensor_count",
            )
            trend["sensor"] = trend["sensor"].str.replace("_detections", "", regex=False).str.upper()
            fig = px.area(
                trend,
                x="date",
                y="sensor_count",
                color="sensor",
                color_discrete_map=SENSOR_COLORS,
                line_group="sensor",
            )
            fig.update_traces(line={"width": 1.8}, opacity=0.68)
            style_chart(fig, 245)
            fig.update_layout(
                xaxis_title=None,
                yaxis_title="Detections",
                legend_title=None,
                hovermode="x unified",
                margin={"l": 8, "r": 8, "t": 12, "b": 5},
            )
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def render_analytics(
    raw: pd.DataFrame,
    groups: pd.DataFrame,
    daily: pd.DataFrame,
    region_shapes: list,
    region_names: list,
    region: str,
    high_threshold: float,
) -> None:
    section_page(
        "Analytics & Insights",
        "Explore observed fire activity, sensor coverage and intensity.",
        "Signal analysis",
    )
    if raw.empty:
        st.info("No detections are available for this filter selection.")
        return

    sensor_daily = daily.melt(
        id_vars="date",
        value_vars=[column for column in daily if column.endswith("_detections")],
        var_name="sensor",
        value_name="sensor_count",
    )
    sensor_daily["sensor"] = sensor_daily["sensor"].str.replace(
        "_detections", "", regex=False
    ).str.upper()
    left, right = st.columns(2)
    with left:
        section_heading("Fire detections over time", "Daily counts by instrument")
        fig = px.line(
            sensor_daily, x="date", y="sensor_count", color="sensor",
            color_discrete_map=SENSOR_COLORS, markers=True,
        )
        fig.update_traces(line_width=2, marker_size=4)
        style_chart(fig, 320)
        fig.update_layout(xaxis_title=None, yaxis_title="Detections/day", legend_title=None,
                          hovermode="x unified")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with right:
        section_heading("Fire intensity distribution", "Fire radiative power · MW")
        intensity = raw[pd.to_numeric(raw["frp"], errors="coerce").notna()].copy()
        fig = px.histogram(
            intensity, x="frp", color="sensor", nbins=36, barmode="overlay",
            opacity=.82, color_discrete_map=SENSOR_COLORS, marginal="box",
        )
        style_chart(fig, 320)
        fig.update_layout(xaxis_title="FRP (MW)", yaxis_title="Observations", legend_title=None)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.caption("FRP is reported per satellite pixel and is not additive across sensors.")

    left, right = st.columns(2)
    with left:
        section_heading("Confidence distribution", "Original sensor confidence classes")
        confidence = (
            raw.groupby(["confidence_class", "sensor"])
            .size().rename("detections").reset_index()
        )
        confidence["confidence_class"] = pd.Categorical(
            confidence["confidence_class"], categories=CONFIDENCE_ORDER, ordered=True
        )
        fig = px.bar(
            confidence, x="confidence_class", y="detections", color="sensor",
            barmode="group", color_discrete_map=SENSOR_COLORS,
            category_orders={"confidence_class": CONFIDENCE_ORDER},
        )
        style_chart(fig, 300)
        fig.update_layout(xaxis_title=None, yaxis_title="Detections", legend_title=None)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with right:
        section_heading("Severity breakdown", "Transparent FRP display bands")
        severity = groups.copy()
        severity["severity"] = severity["max_frp"].map(
            lambda value: severity_for_frp(value, high_threshold)
        )
        counts = severity["severity"].value_counts().reindex(SEVERITY_ORDER, fill_value=0)
        fig = go.Figure(go.Bar(
            x=counts.index,
            y=counts.values,
            marker_color=[SEVERITY_COLORS[level] for level in counts.index],
            hovertemplate="%{x}: %{y:,} incidents<extra></extra>",
        ))
        style_chart(fig, 300)
        fig.update_layout(xaxis_title=None, yaxis_title="Incidents", showlegend=False)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.caption(
            f"Critical ≥ {max(2 * high_threshold, 200):.0f} MW · "
            f"High ≥ {high_threshold:.0f} MW · Medium ≥ {high_threshold / 2:.0f} MW."
        )

    section_heading("Geographic concentration", f"Administrative regions · {region}")
    region_counts = []
    for shape, name in zip(region_shapes, region_names):
        count = int(aoi.inside(raw, shape).sum())
        region_counts.append({"Region": name, "Detections": count})
    region_frame = pd.DataFrame(region_counts).sort_values("Detections", ascending=True)
    fig = px.bar(
        region_frame, x="Detections", y="Region", orientation="h",
        color="Detections", color_continuous_scale=["#63311F", "#FF6B35", "#FFB547"],
    )
    style_chart(fig, max(260, 25 * len(region_frame) + 60))
    fig.update_layout(
        xaxis_title="Observed detections", yaxis_title=None, coloraxis_showscale=False,
        margin={"l": 10, "r": 14, "t": 8, "b": 12},
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})



def render_history(
    raw: pd.DataFrame,
    groups: pd.DataFrame,
    daily: pd.DataFrame,
    region_shapes: list,
    region_names: list,
) -> None:
    """Historical trends: shown at the end of the Analytics & Insights page."""
    st.divider()
    section_heading(
        "Historical trends",
        "Fire activity across dates, regions and times of day from observed FIRMS records",
    )
    if raw.empty or daily.empty:
        st.info("No historical records match the selected filters.")
        return

    daily = daily.copy()
    daily["date"] = pd.to_datetime(daily["date"])
    daily["month"] = daily["date"].dt.to_period("M").dt.to_timestamp()
    monthly = daily.groupby("month", as_index=False).agg(
        detections=("detections", "sum"),
        incidents=("groups", "sum"),
    )
    weekly = daily.set_index("date").resample("W-MON")["detections"].sum().rename("Weekly detections")

    section_heading("Historical activity", "Daily and monthly observed counts")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["detections"], name="Daily detections",
        mode="lines", line={"color": "#FF6B35", "width": 2},
        fill="tozeroy", fillcolor="rgba(255,107,53,.10)",
    ))
    fig.add_trace(go.Scatter(
        x=weekly.index, y=weekly.values, name="Weekly detections",
        mode="lines", line={"color": "#FFB547", "width": 2, "dash": "dot"},
    ))
    style_chart(fig, 330)
    fig.update_layout(xaxis_title=None, yaxis_title="Detections", hovermode="x unified")
    st.plotly_chart(fig, width="stretch")

    left, right = st.columns(2)
    with left:
        section_heading("Monthly comparison", "Counts aggregated from observations")
        if monthly.empty:
            st.info("Monthly summaries are unavailable.")
        else:
            fig = px.bar(
                monthly, x="month", y="detections",
                color="incidents", color_continuous_scale=["#7C321D", "#FF6B35", "#FFB547"],
            )
            style_chart(fig, 300)
            fig.update_layout(xaxis_title=None, yaxis_title="Detections", coloraxis_showscale=False)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with right:
        section_heading("Detection timing", "Day of week × UTC acquisition hour")
        timed = raw.assign(
            hour=raw["datetime_utc"].dt.hour,
            weekday=raw["datetime_utc"].dt.day_name(),
        )
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                         "Friday", "Saturday", "Sunday"]
        hourly = timed.pivot_table(
            index="weekday", columns="hour", values="obs_id", aggfunc="count", fill_value=0
        ).reindex(weekday_order, fill_value=0)
        fig = go.Figure(go.Heatmap(
            z=hourly.to_numpy(),
            x=[f"{hour:02d}:00" for hour in hourly.columns],
            y=weekday_order,
            colorscale=[[0, "#152235"], [.45, "#9A4427"], [1, "#FFB547"]],
            hovertemplate="%{y} · %{x}<br>%{z:,} detections<extra></extra>",
            colorbar={"title": "Count", "tickfont": {"color": "#94A3B8"}},
        ))
        style_chart(fig, 300)
        fig.update_layout(xaxis_title="Acquisition hour (UTC)", yaxis_title=None)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    regional = pd.DataFrame([
        {"Region": name, "Detections": int(aoi.inside(raw, shape).sum())}
        for name, shape in zip(region_names, region_shapes)
    ]).sort_values("Detections", ascending=False)
    # White panel (styled via .st-key-regional_panel in dashboard_theme.py).
    # st.table is plain HTML, so CSS can colour it; st.dataframe can't be.
    with st.container(key="regional_panel"):
        section_heading("Regional fire patterns", "Detection totals by Ghana administrative region")
        regional["Detections"] = regional["Detections"].map("{:,}".format)
        st.table(regional.set_index("Region"))
    with st.expander("Daily historical record", width=560):
        st.dataframe(
            daily.rename(columns={"date": "Date", "detections": "Detections",
                                  "groups": "Incidents", "max_frp": "Peak FRP (MW)"}),
            width="stretch",
            hide_index=True,
        )


def render_data_explorer(raw: pd.DataFrame) -> None:
    section_page(
        "Data Explorer",
        "Review FIRMS files, upload archive exports, or fetch observations from the NASA FIRMS API.",
        "Data operations",
    )
    render_data_manager()
    section_heading("Filtered observations", f"{len(raw):,} rows · current sidebar filters")
    if raw.empty:
        st.info("No observations match the current filters.")
        return
    columns = [
        column for column in (
            "datetime_utc", "sensor", "satellite", "latitude", "longitude",
            "confidence", "confidence_class", "frp", "daynight", "source_file",
        ) if column in raw.columns
    ]
    st.download_button(
        "Download filtered observations",
        data=raw[columns].to_csv(index=False).encode("utf-8"),
        file_name="pyrochronos_filtered_detections.csv",
        mime="text/csv",
    )
    st.dataframe(
        raw[columns].sort_values("datetime_utc", ascending=False),
        width="stretch",
        hide_index=True,
        height=440,
    )


def render_system_information(
    raw: pd.DataFrame,
    groups: pd.DataFrame,
    files: pd.DataFrame,
    region: str,
    settings: dict,
) -> None:
    section_page(
        PAGE_SETTINGS,
        "How PyroChronos processes FIRMS data for Ghana: active settings, method, "
        "data provenance and limitations.",
        "Configuration · technical reference",
    )
    source_label = "Synthetic demo data" if (
        not raw.empty and raw["source_file"].str.startswith(DEMO_PREFIX).any()
    ) else "NASA FIRMS CSV files"
    metrics = [
        ("Data source", source_label),
        ("Area of interest", region),
        ("Detections loaded", f"{len(raw):,}"),
        ("Harmonized groups", f"{len(groups):,}"),
        ("Input files", f"{len(files):,}"),
        ("Processing", "FIRMS CSV → normalized detections → spatial/time groups"),
    ]
    for start in range(0, len(metrics), 2):
        columns = st.columns(2)
        for column, (label, value) in zip(columns, metrics[start:start + 2]):
            with column:
                st.markdown(
                    f'<div class="pc-panel"><div class="pc-muted">{escape(label)}</div>'
                    f'<strong>{escape(value)}</strong></div>',
                    unsafe_allow_html=True,
                )
    st.markdown("")
    with st.expander("Methodology · current settings", expanded=True):
        st.markdown(
            "**Settings** are changed in the sidebar under *Mission filters*; values below "
            "are the ones in use now.\n\n"
            "1. **Ingest** – NASA FIRMS MODIS and VIIRS CSVs for Ghana are normalised to one "
            "table; duplicate detections from overlapping downloads are dropped.\n"
            "2. **Area of interest** – detections are clipped to Ghana's official boundary "
            f"(geoBoundaries) or the chosen region · now: *{region}*.\n"
            "3. **Harmonization** – in time order, a detection joins an open incident if it is "
            f"within **{settings['max_km']:g} km** and **{settings['max_hours']:g} h** of that "
            "incident's latest detection; otherwise it starts a new incident.\n"
            "4. **Alerts (Emberwatch)** – *High intensity*: incident peak FRP ≥ "
            f"**{settings['high_threshold']:g} MW**. *Activity spike*: daily detections above "
            f"the previous 14-day mean + **{settings['spike_sigma']:g} σ**. *Persistent "
            "activity*: an incident observed for 48 h or more. Alerts are labelled with the "
            "nearest town (GeoNames).",
        )
    with st.expander("Data interpretation and limitations", expanded=True):
        st.markdown(
            "- FIRMS hotspots are satellite thermal-anomaly detections, not confirmed "
            "fire perimeters or unique fire incidents.\n"
            "- MODIS and VIIRS have different pixel sizes and confidence scales. Their "
            "FRP values are not directly interchangeable.\n"
            "- Harmonized groups use a configurable distance/time heuristic; separate "
            "nearby fires can merge and a single fire can split.\n"
            "- A missing detection is not evidence that no fire is present. Cloud, smoke, "
            "overpass timing and sensor limits affect coverage.\n"
            "- Rule-based alerts are analytical signals, not emergency warnings.\n"
            "- Alert town names are the nearest listed place, not a confirmed fire location.",
        )
    with st.expander("Data sources and credits"):
        st.markdown(
            "- Fire detections: NASA FIRMS (firms.modaps.eosdis.nasa.gov)\n"
            "- Boundaries: geoBoundaries (geoboundaries.org)\n"
            "- Town names: GeoNames (geonames.org), CC BY 4.0",
        )
    with st.expander("Loaded data files"):
        if files.empty:
            st.info("No CSV files are loaded.")
        else:
            st.dataframe(files.drop(columns="modified"), width="stretch", hide_index=True)


def main() -> None:
    page = st.session_state.get("dashboard_page", PAGE_OVERVIEW)
    page = LEGACY_PAGES.get(page, page)
    if page not in NAV_ITEMS:
        page = PAGE_OVERVIEW
    st.session_state["dashboard_page"] = page

    with st.sidebar:
        # Compact navigation block (styled via .st-key-sidebar_nav in dashboard_theme.py).
        with st.container(key="sidebar_nav"):
            st.markdown(
                '<div class="pc-nav-brand">PyroChronos<span>Ghana wildfire intelligence</span>'
                '</div><div class="pc-nav-label">NAVIGATION</div>',
                unsafe_allow_html=True,
            )
            for index, (item, icon) in enumerate(NAV_ITEMS.items()):
                st.button(
                    item,
                    key=f"dashboard_nav_{index}",
                    icon=icon,
                    type="primary" if page == item else "secondary",
                    width="stretch",
                    on_click=go_to,
                    args=(item,),
                )
        st.divider()
        st.markdown(
            '<div style="color:#FF9A64;font-size:.69rem;font-weight:700;letter-spacing:.15em">'
            'MISSION FILTERS</div>',
            unsafe_allow_html=True,
        )

        max_km = st.slider("Incident merge distance · km", .5, 10.0, 2.0, .5)
        max_hours = st.slider("Incident merge window · hours", 1, 72, 24)

    raw_all, groups_all = load_data(max_km, max_hours, data_fingerprint())
    files = list_raw_files()
    connected = not raw_all.empty
    sync_label = (
        datetime.fromtimestamp(float(files["modified"].max())).strftime("%d %b %Y · %H:%M")
        if not files.empty else "No source files"
    )

    region_path = aoi.BOUNDARY_DIR / "ghana_regions.geojson"
    country_path = aoi.BOUNDARY_DIR / "ghana_country.geojson"
    region_shapes, region_names = load_boundary(str(region_path), region_path.stat().st_mtime)
    country_shapes, _ = load_boundary(str(country_path), country_path.stat().st_mtime)
    region_options = ["All Ghana"] + region_names + ["Ghana bounding box"]

    if not raw_all.empty:
        with st.sidebar:
            region = st.selectbox("Geographic region", region_options, index=0)
            dates = pd.to_datetime(raw_all["date"])
            min_date, max_date = dates.min().date(), dates.max().date()
            selected_dates = st.date_input(
                "Observation date range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                format="DD/MM/YYYY",
            )
            if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
                start_date, end_date = selected_dates
            elif isinstance(selected_dates, date):
                start_date = end_date = selected_dates
            else:
                start_date, end_date = min_date, max_date

            confidence_options = [
                level for level in CONFIDENCE_ORDER
                if level in set(raw_all["confidence_class"].astype(str))
            ]
            confidence = st.multiselect(
                "Fire confidence", confidence_options, default=confidence_options
            )
            sensor_options = sorted(raw_all["sensor"].dropna().astype(str).unique())
            sensors = st.multiselect("Satellite instrument", sensor_options, default=sensor_options)
            satellite_options = sorted(raw_all["satellite"].dropna().astype(str).unique())
            satellites = st.multiselect(
                "Satellite source", satellite_options, default=satellite_options
            )
            max_frp = max(100, int(math.ceil(float(raw_all["frp"].max()) / 50) * 50))
            frp_range = st.slider(
                "Fire intensity · FRP MW", 0, max_frp, (0, max_frp), step=10
            )
            alert_severities = st.multiselect(
                "Alert severity", SEVERITY_ORDER, default=SEVERITY_ORDER
            )
            high_threshold = st.number_input(
                "High-intensity alert threshold · MW",
                min_value=20,
                max_value=1000,
                value=100,
                step=10,
                key="alert_frp_threshold",
            )
            spike_sigma = st.slider("Activity spike sensitivity · σ", 1.0, 4.0, 2.0, .5)

            st.divider()
            st.caption(
                f"{len(raw_all):,} source detections · {len(sensor_options)} instruments · Ghana AOI"
            )
    else:
        region, start_date, end_date = "All Ghana", date.today(), date.today()
        confidence, sensors, satellites = [], [], []
        frp_range, high_threshold, spike_sigma = (0, 100), 100.0, 2.0
        alert_severities = SEVERITY_ORDER

    if region == "All Ghana":
        geometry = aoi.merge(region_shapes)
    elif region == "Ghana bounding box":
        geometry = aoi.box_shape(AREAS["Ghana"])
    else:
        geometry = region_shapes[region_names.index(region)]

    if raw_all.empty:
        filtered_raw = raw_all
        filtered_groups = groups_all
    else:
        region_mask = aoi.inside(raw_all, geometry)
        filtered_raw = raw_all[
            region_mask
            & raw_all["date"].between(start_date, end_date)
            & raw_all["confidence_class"].isin(confidence)
            & raw_all["sensor"].isin(sensors)
            & raw_all["satellite"].astype(str).isin(satellites)
            & raw_all["frp"].fillna(0).between(*frp_range)
        ].copy()
        if filtered_raw.empty:
            filtered_groups = groups_all.iloc[0:0].copy()
        else:
            filtered_group_ids = filtered_raw["group_id"].unique()
            filtered_groups = groups_all[
                groups_all["group_id"].isin(filtered_group_ids)
                & groups_all["date"].between(start_date, end_date)
                & aoi.inside(groups_all, geometry)
                & groups_all["max_frp"].fillna(0).between(*frp_range)
            ].copy()

    daily = daily_summary(filtered_raw, filtered_groups)
    alert_signals = build_alerts(
        daily, filtered_groups, spike_sigma=spike_sigma, frp_threshold=high_threshold
    )
    alert_table = make_alert_table(
        alert_signals, filtered_raw, filtered_groups, region_shapes, region_names, high_threshold
    )
    render_topbar(sync_label, connected, int(len(alert_table)))

    if raw_all.empty:
        render_hero(
            "Wildfire Intelligence Center",
            "Real-time wildfire monitoring, geospatial intelligence and environmental risk analytics.",
        )
        st.info("No FIRMS detections are loaded. Add source data in Data Explorer to begin.")
        render_data_manager()
        return

    if filtered_raw["source_file"].str.startswith(DEMO_PREFIX).any():
        st.warning(
            "Synthetic demonstration observations are included in this view; "
            "they are not NASA FIRMS records.",
            icon="⚠️",
        )
    if filtered_raw.empty:
        render_hero(
            "No detections in this view",
            "Adjust the date, region, sensor, confidence or intensity filters to explore observations.",
            "Filters active",
        )
        st.info("The selected filters returned no observations.")
        if page == PAGE_DATA:
            render_data_manager()
        return

    period_label = f"{start_date:%d %b} – {end_date:%d %b %Y}"
    if page == PAGE_OVERVIEW:
        render_overview(
            filtered_raw, filtered_groups, daily, geometry, alert_table,
            high_threshold, period_label,
        )
    elif page == PAGE_MAP:
        section_page(
            "Fire Detection Map",
            "Explore clustered MODIS/VIIRS detections across selected basemaps.",
            f"Geospatial intelligence · {region}",
        )
        # Map detail on the left, a narrow Basemap picker pushed to the right edge.
        detail_col, _, basemap_col = st.columns([3, 2, 1.2], vertical_alignment="bottom")
        with detail_col:
            # A radio (styled in dashboard_theme.py) stays readable in every
            # state; Streamlit's segmented control kept dark-on-dark text here.
            map_view = st.radio(
                "Map detail",
                ["Individual detections", "Harmonized incidents"],
                horizontal=True,
                key="map_detail_view",
            )
        with basemap_col:
            basemap = st.selectbox(
                "Basemap",
                ["Dark intelligence", "Satellite imagery", "Terrain", "Light reference"],
            )
        if map_view is None:
            map_view = "Individual detections"
        shown_groups = filtered_groups if map_view == "Harmonized incidents" else (
            filtered_groups.iloc[0:0]
        )
        render_fire_map(
            filtered_raw, shown_groups, geometry, height=650, basemap=basemap,
            show_heatmap=True, key="detailed_fire_map",
        )
    elif page == PAGE_ANALYTICS:
        render_analytics(
            filtered_raw, filtered_groups, daily, region_shapes, region_names, region,
            high_threshold,
        )
        render_history(filtered_raw, filtered_groups, daily, region_shapes, region_names)
    elif page == PAGE_ALERTS:
        section_page(
            PAGE_ALERTS,
            "Search and triage transparent rule-based signals derived from observed FIRMS detections.",
            "Response queue · session-only status",
        )
        render_alerts(
            daily, filtered_raw, filtered_groups, region_shapes, region_names,
            spike_sigma, high_threshold, alert_severities,
        )
    elif page == PAGE_DATA:
        render_data_explorer(filtered_raw)
    else:  # PAGE_SETTINGS
        render_system_information(
            filtered_raw, filtered_groups, files, region,
            {"max_km": max_km, "max_hours": max_hours,
             "high_threshold": high_threshold, "spike_sigma": spike_sigma},
        )



if __name__ == "__main__":
    main()
