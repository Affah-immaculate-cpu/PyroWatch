# PyroChronos

A Streamlit wildfire-intelligence dashboard for exploring NASA FIRMS MODIS and
VIIRS thermal-anomaly observations over Ghana. It includes an interactive map,
historical analysis, alert summaries, and an experimental next-day model.

> FIRMS detections are satellite observations, not confirmed fire perimeters or
> emergency warnings. Model outputs and derived severity labels are exploratory.

## Run locally

The Streamlit application and its full documentation are in [`pyrochronos/`](./pyrochronos/).

```powershell
Set-Location pyrochronos
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The dashboard opens at <http://localhost:8501>. Python 3.10 or newer and an
internet connection for map tiles are recommended.

## FIRMS API access

To fetch data directly from NASA FIRMS, set `FIRMS_MAP_KEY` in
`pyrochronos/.streamlit/secrets.toml`, or enter the key in the application.
Never commit `secrets.toml`; the project ignores it. A FIRMS key is not needed
to display the basemaps or explore already-loaded data.

See [`pyrochronos/README.md`](./pyrochronos/README.md) for dashboard sections,
data setup, and interpretation notes.
