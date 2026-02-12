# Microcosm

Get a GeoJSON file of OpenStreetMap data, updated nightly, by writing one Overpass query. Useful for any occassion where you need a very narrow slice of OSM data (10's of MB) but don't need it to fresh to the minute.

## Quick start

1. **Fork this repository** click "Use this template" > "Create a new respository", give it a descriptive name.
2. **Edit `query.overpassql`** with your own Overpass query
3. **Run the workflow manually**: go to **Actions** > **"Update GeoJSON Data"** > **"Run workflow"**
4. **Check `data.geojson`** - it should now contain your data

From now on, your data will update automatically every night at 04:00 UTC.

## Writing your query

Edit `query.overpassql` with any valid Overpass QL query. Your query **must**:

- Start with `[out:json]` so the response is JSON
- Include a `[timeout:N]` setting (30 seconds is fine for small queries, increase for larger ones)
- For full geometry (polygons, linestrings), use `out body geom;`
- For centroids only (every element becomes a point), use `out center body;`

To define a search area, use `rel(<OSM relation ID>)` + `map_to_area`. You can find relation IDs on [openstreetmap.org](https://www.openstreetmap.org/) or via [Nominatim](https://nominatim.openstreetmap.org/). For example, Portland, OR is relation [186579](https://www.openstreetmap.org/relation/186579):

```
[out:json][timeout:30];
rel(186579);
map_to_area->.searchArea;
(
  nwr["amenity"="drinking_water"](area.searchArea);
);
out body geom;
```

Test your query at [overpass-turbo.eu](https://overpass-turbo.eu/) first to make sure it returns the data you expect.

## Safety checks

The workflow includes guards to prevent bad data from being committed:

- **Empty response**: If the Overpass API returns an error or zero features, the workflow fails and your existing data is preserved
- **Large drop detection**: If the new data has significantly fewer features than the existing file (default: >50% drop), the workflow fails with a warning - this catches partial Overpass responses

These settings can be adjusted via **GitHub repository variables** (Settings > Secrets and variables > Actions > Variables). No code changes needed.

| Variable             | Default | Description                                                           |
| -------------------- | ------- | --------------------------------------------------------------------- |
| `DROP_THRESHOLD`     | `50`    | Maximum allowed percentage drop in feature count before failing (0-100) |
| `MAX_DATA_LAG_HOURS` | `48`    | Maximum age of Overpass data in hours before trying another server     |

## Output format

`data.geojson` is a standard [GeoJSON](https://geojson.org/) FeatureCollection. Each OSM element becomes a Feature with:

- **Geometry**: Point, LineString, Polygon, MultiPolygon, or MultiLineString depending on the element type and tags
- **Properties**: all OSM tags, plus `@id` (e.g., `node/12345`) and `@type` (`node`, `way`, or `relation`)

## Using the data

The raw `data.geojson` URL from your repository works directly with many tools:

- **GitHub** renders GeoJSON files as interactive maps automatically
- **[geojson.io](https://geojson.io/)** - paste the raw URL to view and edit
- **Leaflet / MapLibre / Mapbox GL** - load as a GeoJSON data source
- **QGIS** - add as a vector layer via URL
- **[Ultra](https://overpass-ultra.us/)** - add as a vector layer via URL
