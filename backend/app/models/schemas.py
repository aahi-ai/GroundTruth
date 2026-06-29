from pydantic import BaseModel
from typing import List, Optional

class FieldBoundaryRequest(BaseModel):
    """
    The frontend sends a field boundary as GeoJSON-style coordinats:
    a list of [longitude, latitude] pairs forming a closed polygon ring.
    """
    coordinates: List[List[float]]

class NDVIResponse(BaseModel):
    scene_date: str
    cloud_cover: float
    ndvi_mean: float
    ndvi_grid: List[List[Optional[float]]]
    grid_shape: List[int]