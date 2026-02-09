[out:json][timeout:30];
area["name"="Portland"]["admin_level"="8"]["is_in:state"="Oregon"]->.searchArea;
(
  nwr["amenity"="drinking_water"](area.searchArea);
);
out body geom;
