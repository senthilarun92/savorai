import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.services.vision_service import analyze_food_image
from app.auth.dependencies import get_current_user
from app.models import User

router = APIRouter(
    prefix="/api/camera",
    tags=["Camera"]
)


@router.post("/analyze")
async def analyze_camera_image(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Only image files are allowed"
        )

    image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Image file is empty"
        )

    if len(image_bytes) > 20 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Image size must be 20MB or less"
        )

    try:
        result = analyze_food_image(image_bytes)
        detected = json.loads(result)

        if not isinstance(detected, dict):
            raise ValueError("Invalid AI response")

        ingredients = detected.get("ingredients", [])

        if not isinstance(ingredients, list):
            raise ValueError("Invalid ingredients format")

        return {
            "message": "Ingredients detected successfully",
            "ingredients": ingredients
        }

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail="Vision AI returned invalid JSON"
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Vision AI service error: {str(exc)}"
        )


