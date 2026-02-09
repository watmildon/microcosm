# tap-in-osm

Get a GeoJSON file of OpenStreetMap data, updated nightly, by writing one Overpass query. Useful for any occassion where you need a very narrow slice of OSM data (10's of MB) but don't need it to fresh to the minute.

## How it works

1. Reads the Overpass query in `query.overpassql`
2. Every night, a GitHub Actions workflow sends that query to the Overpass API
3. The response is converted to a GeoJSON file with full geometry and committed back to this repository
4. You always have a fresh `data.geojson` you can link to, download, or use in other tools

## Quick start

1. **Fork this repository** (or click "Use this template" if available)
2. **Enable GitHub Actions** on your fork - GitHub disables Actions on forks by default. Go to the **Actions** tab and click **"I understand my workflows, go ahead and enable them"**
3. **Edit `query.overpassql`** with your own Overpass query
4. **Run the workflow manually**: go to **Actions** > **"Update GeoJSON Data"** > **"Run workflow"**
5. **Check `data.geojson`** - it should now contain your data

From now on, the data updates automatically every night at 04:00 UTC.

## Writing your query

Edit `query.overpassql` with any valid Overpass QL query. Your query **must**:

- Start with `[out:json]` so the response is JSON
- Include a `[timeout:N]` setting (30 seconds is fine for small queries, increase for larger ones)
- For full geometry (polygons, linestrings), use `out body geom;`:
- For centroids only (every element becomes a point), use `out center body;`:

Test your query at [overpass-turbo.eu](https://overpass-turbo.eu/) first to make sure it returns the data you expect.

## Geometry handling

The conversion preserves full OSM geometry:

| OSM element                  | Output geometry           |
| ---------------------------- | ------------------------- |
| Node                         | Point                     |
| Way (open)                   | LineString                |
| Way (closed + area tags)     | Polygon                   |
| Relation (type=multipolygon) | MultiPolygon (with holes) |
| Relation (type=route)        | MultiLineString           |

Closed ways are treated as Polygons when they have area-indicating tags like `building`, `landuse`, `natural`, `leisure`, `amenity`, `boundary`, etc. A closed way without these tags (e.g., a circular road) stays a LineString.

If you use `out center` instead of `out geom`, all elements become Points at their centroid.

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