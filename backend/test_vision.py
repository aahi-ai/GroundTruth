from app.services.vision import analyze_plant_photo

with open("test_photo.jpg", "rb") as f:
    image_bytes = f.read()

result = analyze_plant_photo(image_bytes)
print(result)