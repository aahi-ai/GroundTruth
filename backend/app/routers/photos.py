from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.vision import analyze_plant_photo

router = APIRouter(prefix="/photos", tags=["photos"])


@router.post("/analyze")
async def analyze_photo(file: UploadFile = File(...)):
    """
    Accepts an uploaded plant/crop photo and returns a stress assessment:
    a 0-100 health score, a plain-language summary, and any detected issues.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be an image.",
        )

    image_bytes = await file.read()

    try:
        result = analyze_plant_photo(image_bytes, media_type=file.content_type)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return result