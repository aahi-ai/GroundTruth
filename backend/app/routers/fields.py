from fastapi import APIRouter, HTTPException

from app.models.schemas import FieldBoundaryRequest, NDVIResponse
from app.services.satellite import fetch_ndvi_for_field

router = APIRouter(prefix="/fields", tags=["fields"])


@router.post("/ndvi", response_model=NDVIResponse)
def get_field_ndvi(field: FieldBoundaryRequest):
    """
    Given a field boundary (polygon coordinates), fetch the latest
    cloud-free Sentinel-2 scene and return the NDVI grid for that field.
    """
    field_geojson = {
        "type": "Polygon",
        "coordinates": [field.coordinates],
    }

    try:
        result = fetch_ndvi_for_field(field_geojson)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "scene_date": result["scene_date"],
        "cloud_cover": result["cloud_cover"],
        "ndvi_mean": result["ndvi_mean"],
        "ndvi_grid": result["ndvi_grid"],
        "grid_shape": list(result["grid_shape"]),
    }

