from app.services.satellite import fetch_ndvi_for_field

test_field = {
    "type": "Polygon",
    "coordinates": [[
        [-93.6200, 42.0300],
        [-93.6150, 42.0300],
        [-93.6150, 42.0340],
        [-93.6200, 42.0340],
        [-93.6200, 42.0300]
    ]]
}

result = fetch_ndvi_for_field(test_field)
print("Scene date:", result["scene_date"])
print("Cloud cover:", result["cloud_cover"])
print("NDVI mean:", result["ndvi_mean"])
print("Grid Shape:", result["grid_shape"])