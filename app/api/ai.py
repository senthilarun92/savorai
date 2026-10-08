import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models import User
from app.recipe_models import Recipe
from app.schemas.recipe import RecipeResponse
from app.services.groq_service import generate_text

router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.post("/recipe", response_model=dict)
def generate_recipe(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ingredients = data.get("ingredients")
    cuisine = data.get("cuisine", "Any")
    diet = data.get("diet", "Any")
    language = data.get("language", "English")
    dish_name = data.get("dish_name")
    user_id = current_user.id

    if not ingredients:
        raise HTTPException(
            status_code=400,
            detail="ingredients are required"
        )

    if user_id:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

    prompt = f"""
You are an expert AI chef.

Create one practical recipe using these ingredients:
{ingredients}

Preferred dish: {dish_name or "Choose a suitable dish from the ingredients"}

Cuisine: {cuisine}
Diet: {diet}
Language: {language}

Return ONLY valid JSON.
Do not use markdown.
Do not use ```.

Use exactly this structure:

{{
  "title": "Recipe title",
  "description": "Short description",
  "servings": 2,
  "prep_time": 10,
  "cook_time": 20,
  "difficulty": "Easy",
  "ingredients": [
    {{
      "name": "ingredient name",
      "quantity": "quantity"
    }}
  ],
  "instructions": [
    "Step 1",
    "Step 2"
  ],
  "nutrition": {{
    "calories": "300 kcal",
    "protein": "10 g",
    "carbs": "45 g",
    "fat": "8 g"
  }},
  "chef_tips": [
    "Tip 1",
    "Tip 2"
  ]
}}

Use the requested language: {language}.
Keep the recipe realistic and easy to follow.
"""

    try:
        result = generate_text(prompt)

        try:
            recipe_data = json.loads(result)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=502,
                detail="AI returned invalid JSON"
            )

        try:
            validated_recipe = RecipeResponse.model_validate(recipe_data)
        except Exception:
            raise HTTPException(
                status_code=502,
                detail="AI returned an invalid recipe structure"
            )

        recipe = Recipe(
            user_id=current_user.id,
            title=validated_recipe.title,
            description=validated_recipe.description,
            cuisine=cuisine,
            diet=diet,
            language=language,
            servings=validated_recipe.servings,
            prep_time=validated_recipe.prep_time,
            cook_time=validated_recipe.cook_time,
            difficulty=validated_recipe.difficulty,
            ingredients=json.dumps(
                [item.model_dump() for item in validated_recipe.ingredients],
                ensure_ascii=False
            ),
            instructions=json.dumps(
                validated_recipe.instructions,
                ensure_ascii=False
            ),
            nutrition=json.dumps(
                validated_recipe.nutrition.model_dump(),
                ensure_ascii=False
            ),
        )

        db.add(recipe)
        db.commit()
        db.refresh(recipe)

        return {
            "message": "Recipe generated and saved successfully",
            "recipe_id": recipe.id,
            "user_id": user_id,
            "recipe": validated_recipe.model_dump()
        }

    except HTTPException:
        raise

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail=f"AI service error: {str(exc)}"
        )

@router.post("/suggestions", response_model=dict)
def generate_suggestions(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ingredients = data.get("ingredients")
    cuisine = data.get("cuisine", "Any")
    diet = data.get("diet", "Any")
    language = data.get("language", "English")
    dish_name = data.get("dish_name")
    user_id = current_user.id

    if not ingredients:
        raise HTTPException(
            status_code=400,
            detail="ingredients are required"
        )

    if user_id:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

    prompt = f"""
You are an expert AI chef.

Create exactly 5 distinct practical recipe ideas using these ingredients:
{ingredients}

Preferred dish: {dish_name or "Choose a suitable dish from the ingredients"}

Cuisine: {cuisine}
Diet: {diet}
Language: {language}

Return ONLY valid JSON.
Do not use markdown.
Do not use ```.

Use exactly this structure:

{{
  "recipes": [
    {{
      "name": "Recipe name",
      "description": "Short description"
    }}
  ]
}}

Requirements:
- Return exactly 5 recipe ideas.
- Each recipe must be different.
- Use the available ingredients realistically.
- Do not include full instructions.
- Do not include nutrition information.
- Use the requested language: {language}.
"""

    try:
        result = generate_text(prompt)

        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=502,
                detail="AI returned invalid JSON"
            )

        recipes = parsed.get("recipes", [])

        if not isinstance(recipes, list):
            raise HTTPException(
                status_code=502,
                detail="AI returned invalid recipe suggestions"
            )

        cleaned_recipes = []

        for item in recipes[:5]:
            if isinstance(item, dict) and item.get("name"):
                cleaned_recipes.append({
                    "name": str(item["name"]),
                    "description": str(
                        item.get("description", "")
                    )
                })

        if not cleaned_recipes:
            raise HTTPException(
                status_code=502,
                detail="AI returned no recipe suggestions"
            )

        return {
            "recipes": cleaned_recipes
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI service error: {str(exc)}"
        )







