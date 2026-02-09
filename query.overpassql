// Output format: JSON with 30 second timeout
[out:json][timeout:30];

// Define search area using an OSM relation ID
// Find relation IDs at https://nominatim.openstreetmap.org
// ex, Portland, OR: https://www.openstreetmap.org/relation/186579
rel(186579);
map_to_area->.searchArea;

// Query: all drinking water fountains in the search area
(
  nwr["amenity"="drinking_water"](area.searchArea);
);

// Output full geometry (use "out center body;" for centroids only)
out body geom;
