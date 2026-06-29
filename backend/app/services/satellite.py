from datetime import datetime, timedelta, timezone

import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import transform_geom
import pystac_client
import planetary_computer
from shapely.geometry import shape, mapping


STAC_API_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"


def fetch_ndvi_for_field(
    field_geojson: dict,
    max_cloud_cover: int = 20,
    lookback_days: int = 60,
):
    """
    Given a field boundary as GeoJSON (a Polygon), find the most recent
    cloud-free Sentinel-2 scene, compute NDVI, and clip it to the field.

    Returns a dict with the NDVI grid (as a nested list) and basic metadata.
    """
    field_polygon = shape(field_geojson)
    bbox = field_polygon.bounds 

    catalog = pystac_client.Client.open(
        STAC_API_URL,
        modifier=planetary_computer.sign_inplace,
    )

    items = []
    window_days = lookback_days
    for _ in range(3): 
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=window_days)
        date_range = f"{start.date().isoformat()}/{end.date().isoformat()}"

        search = catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime=date_range,
            query={"eo:cloud_cover": {"lt": max_cloud_cover}},
            sortby="-datetime",
            max_items=1,
        )
        items = list(search.item_collection())
        if items:
            break
        window_days *= 3  

    if not items:
        raise ValueError(
            "No cloud-free Sentinel-2 scenes found for this field in the "
            "searched time window. Try a less strict max_cloud_cover."
        )

    item = items[0]
    scene_date = item.datetime.isoformat()

    red_href = item.assets["B04"].href
    nir_href = item.assets["B08"].href

    red_array, red_transform, red_crs = _read_clipped_band(red_href, field_polygon)
    nir_array, _, _ = _read_clipped_band(nir_href, field_polygon)

    red = red_array.astype(np.float32)
    nir = nir_array.astype(np.float32)
    ndvi = (nir - red) / (nir + red + 1e-6)

    ndvi = np.where((red_array == 0) & (nir_array == 0), np.nan, ndvi)

    return {
        "scene_date": scene_date,
        "cloud_cover": item.properties.get("eo:cloud_cover"),
        "ndvi_mean": float(np.nanmean(ndvi)),
        "ndvi_grid": [
            [None if np.isnan(val) else float(val) for val in row]
            for row in np.round(ndvi, 3)
        ],
        "grid_shape": ndvi.shape,
    }


def _read_clipped_band(href: str, field_polygon):
    """Open a single satellite band and clip it to the field polygon."""
    with rasterio.open(href) as src:
        geom_in_raster_crs = transform_geom(
            "EPSG:4326", src.crs, mapping(field_polygon)
        )
        clipped, transform = mask(src, [geom_in_raster_crs], crop=True, nodata=0)
        return clipped[0], transform, src.crs
