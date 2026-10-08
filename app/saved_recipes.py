import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.saved_recipe_models import SavedRecipe
from app.recipe_models import Recipe
from app.models import User
from app.auth.dependencies import get_current_user

router = APIRouter(
    prefix="/api/saved-recipes",
    tags=["Saved Recipes"]
)


def parse_json(value, default):
    if not value:
        return default

    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


@router.post("")
def save_recipe(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)): 
    user_id = current_user.id
    recipe_id = data.get("recipe_id")

    if not user_id or not recipe_id:
        raise HTTPException(
            status_code=400,
            detail="recipe_id is required"
        )

    user_id = current_user.id

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.user_id == current_user.id).first()

    if not recipe:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found"
        )

    existing_saved = db.query(SavedRecipe).filter(
        SavedRecipe.user_id == current_user.id,
        SavedRecipe.recipe_id == recipe_id
    ).first()

    if existing_saved:
        raise HTTPException(
            status_code=409,
            detail="Recipe already saved"
        )

    saved_recipe = SavedRecipe(
        user_id=user_id,
        recipe_id=recipe_id
    )

    db.add(saved_recipe)
    db.commit()
    db.refresh(saved_recipe)

    return {
        "message": "Recipe saved successfully",
        "id": saved_recipe.id,
        "user_id": current_user.id,
        "recipe_id": recipe_id
    }


@router.get("")
def get_saved_recipes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)): 
    user_id = current_user.id

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    saved_recipes = (
        db.query(SavedRecipe, Recipe)
        .join(Recipe, SavedRecipe.recipe_id == Recipe.id)
        .filter(SavedRecipe.user_id == user_id)
        .order_by(SavedRecipe.saved_at.desc())
        .all()
    )

    return [
        {
            "saved_id": saved.id,
            "recipe_id": recipe.id,
            "title": recipe.title,
            "description": recipe.description,
            "cuisine": recipe.cuisine,
            "diet": recipe.diet,
            "language": recipe.language,
            "servings": recipe.servings,
            "prep_time": recipe.prep_time,
            "cook_time": recipe.cook_time,
            "difficulty": recipe.difficulty,
            "ingredients": parse_json(recipe.ingredients, []),
            "instructions": parse_json(recipe.instructions, []),
            "nutrition": parse_json(recipe.nutrition, {}),
            "saved_at": saved.saved_at
        }
        for saved, recipe in saved_recipes
    ]


@router.delete("/{recipe_id}")
def delete_saved_recipe(recipe_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    saved_recipe = db.query(SavedRecipe).filter(
        SavedRecipe.user_id == current_user.id,
        SavedRecipe.recipe_id == recipe_id
    ).first()

    if not saved_recipe:
        raise HTTPException(
            status_code=404,
            detail="Saved recipe not found"
        )

    db.delete(saved_recipe)
    db.commit()

    return {
        "message": "Recipe removed from saved recipes",
        "user_id": current_user.id,
        "recipe_id": recipe_id
    }














