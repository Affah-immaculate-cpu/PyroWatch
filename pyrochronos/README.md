# PyroChronos — Wildfire Intelligence Center

PyroChronos is a Streamlit dashboard for exploring NASA FIRMS MODIS and VIIRS
thermal-anomaly observations over Ghana and nearby areas. It combines a clustered
geospatial map, transparent alert rules, historical summaries, and an experimental
next-day model in a dark command-center interface.

FIRMS detections are satellite observations, not confirmed fire perimeters or
emergency warnings. Interpret derived groups and severity labels as analytical
summaries, not official incident assessments.

## Run locally

Open a terminal in this directory (`D:\PyroChronos\pyrochronos` on the current
Windows installation), then create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The dashboard opens at <http://localhost:8501>. If the environment is already
installed, launch it from this directory with:

```powershell
python -m streamlit run app.py
```

Python 3.10 or newer is recommended. Map basemaps require an internet connection.

## Dashboard sections

Use the collapsible sidebar navigation to switch between:

1. **Overview** — detection, recent-incident, high-risk, and latest-observation
   metrics, with a clustered map, daily trend, and priority alert signals.
2. **Fire Detection Map** — an interactive orthographic 3D globe with a
   rotate-and-zoom animation, plus individual detections or harmonized incidents
   on selectable dark, satellite, terrain, and light basemaps. Detection density
   is shown by default. Display basemaps do not require a key; a FIRMS MAP_KEY is
   only needed to fetch data from the FIRMS API.
3. **Analytics & Insights** — daily sensor trends, FRP and confidence distributions,
   transparent FRP severity bands, and geographic concentration.
4. **Historical Analysis** — daily/weekly/monthly activity, acquisition-time
   patterns, and regional summaries for the selected date range.
5. **Alert Management** — next-day hotspot predictions alongside searchable,
   severity-filtered rule matches. Alert status changes are held in the current
   Streamlit session; they are not sent as notifications.
6. **Data Explorer** — manage FIRMS files and API downloads, inspect filtered records,
   and export the current selection as CSV.
7. **System Information** — input-file and processing summaries plus interpretation
   and model limitations.

The sidebar filters apply across views: region, observation dates, confidence class,
instrument, satellite, FRP range, alert severity, incident-matching distance and
time window, and activity-spike sensitivity. Filters only describe the loaded data;
the application does not generate unsupported statistics for empty selections.

## Data sources

Place FIRMS CSV downloads in the matching folders:

```text
data/
├── raw/
│   ├── modis/
│   └── viirs/
├── training/
│   ├── modis/
│   └── viirs/
└── processed/
```

Keep the datasets separate:

- `data/raw/modis/` and `data/raw/viirs/` are for observations displayed in the
  dashboard. The existing display CSVs stay here.
- `data/training/modis/` and `data/training/viirs/` are for FIRMS-format CSVs
  used to generate hotspot predictions. The model loader reads only these folders;
  their CSVs do not get added to dashboard maps, counts, or rule-based alerts.

To generate predictions, add training CSVs to the matching `data/training/`
sensor folder, open **Alert Management**, and select **Generate next-day
predictions**. At least 10 distinct observation dates are required. The
interface displays the prediction results, not the training records.

To train and save a reusable model artifact, run this command from the
`pyrochronos` project folder:

```powershell
python scripts/train_hotspot_model.py
```

It saves the fitted estimator, feature settings, training date, and held-out
evaluation metrics to `models/hotspot_model.joblib`. Rerun the command after
adding newer training CSVs to refresh the saved model. The dashboard's prediction
button still trains from the current training CSVs for its session; it does not
load the saved artifact automatically.

The data manager also supports uploading FIRMS CSV files and fetching observations
through the FIRMS API. To enable API access, copy
`.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and set your own key:

```toml
FIRMS_MAP_KEY = "your-key"
```

Alternatively, enter the key in the app when prompted. Keep `secrets.toml` private;
it is excluded from Git. The app preserves source observations and derives
harmonized groups using the sidebar's configurable time/distance heuristic. Changes
to files under `data/raw/` invalidate the cached source data.

## Project structure

```text
app.py                    Streamlit pages, filters, map, charts, and dispatch
ui_data.py                FIRMS upload, API download, and data management UI
utils/dashboard_theme.py  Shared visual theme and dashboard components
pyro/                     Processing, Ghana boundaries, alerts, FIRMS API, model
data/raw/                 Source FIRMS CSV files (MODIS and VIIRS)
data/training/            Separate FIRMS CSVs used to generate predictions
data/processed/           Optional processed-data exports
models/                   Saved model artifacts
scripts/                  Data fetch, model training, demo generation, and processing
ml/ models/ pages/        Extension points for project modules and pages
```

## Interpretation notes

- FIRMS points represent thermal anomalies detected during satellite overpasses;
  they do not establish a unique fire or its perimeter.
- MODIS and VIIRS differ in footprint and confidence definitions. The app retains
  their source confidence classes and uses normalized classes only for filtering.
- Harmonized groups are heuristic: nearby independent fires may merge, and a single
  fire may split into multiple groups.
- FRP is not additive across detections or sensors. Incident summaries use peak FRP.
  Severity bands are configurable display classifications, not official ratings.
- Missing detections do not prove that no fire is present; clouds, smoke, overpass
  timing, and sensor coverage affect observations.
- Alert rules summarize activity spikes, high FRP, and persistence. They do not
  dispatch alerts or replace emergency services.
- Next-day hotspot predictions use prior detections and seasonality, not weather,
  vegetation, or land cover. They are estimates, not official warnings or an
  operational fire forecast.

## Troubleshooting

**`ModuleNotFoundError: pyro`** — Run Streamlit from this project directory.

**`requirements.txt` not found** — Change into `D:\PyroChronos\pyrochronos` before installing.

**No observations are shown** — Check the CSVs in `data/raw/modis/` and `data/raw/viirs/`, then use Data Explorer to reload or fetch data.

**Basemap tiles do not load** — Check the internet connection; the map tiles are provided by external tile services.
