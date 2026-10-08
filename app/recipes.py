import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models import User
from app.recipe_models import Recipe

router = APIRouter(prefix="/api/recipes", tags=["Recipes"])


def parse_json(value, default):
    if not value:
        return default

    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def recipe_to_dict(recipe):
    return {
        "id": recipe.id,
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
        "created_at": recipe.created_at,
    }


@router.get("")
def get_recipes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recipes = (
        db.query(Recipe)
        .filter(Recipe.user_id == current_user.id)
        .order_by(Recipe.created_at.desc())
        .all()
    )

    return [recipe_to_dict(recipe) for recipe in recipes]


@router.get("/{recipe_id}")
def get_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recipe = (
        db.query(Recipe)
        .filter(
            Recipe.id == recipe_id,
            Recipe.user_id == current_user.id,
        )
        .first()
    )

    if not recipe:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found"
        )

    return recipe_to_dict(recipe)


@router.post("")
def create_recipe(
    recipe_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    title = recipe_data.get("title")

    if not title:
        raise HTTPException(
            status_code=400,
            detail="title is required"
        )

    recipe = Recipe(
        user_id=current_user.id,
        title=title,
        description=recipe_data.get("description"),
        cuisine=recipe_data.get("cuisine"),
        diet=recipe_data.get("diet"),
        language=recipe_data.get("language"),
        servings=recipe_data.get("servings"),
        prep_time=recipe_data.get("prep_time"),
        cook_time=recipe_data.get("cook_time"),
        difficulty=recipe_data.get("difficulty"),
        ingredients=json.dumps(
            recipe_data.get("ingredients", []),
            ensure_ascii=False
        ),
        instructions=json.dumps(
            recipe_data.get("instructions", []),
            ensure_ascii=False
        ),
        nutrition=json.dumps(
            recipe_data.get("nutrition", {}),
            ensure_ascii=False
        ),
    )

    db.add(recipe)
    db.commit()
    db.refresh(recipe)

    return {
        "message": "Recipe created successfully",
        "id": recipe.id,
        "title": recipe.title,
    }


@router.put("/{recipe_id}")
def update_recipe(
    recipe_id: int,
    recipe_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recipe = (
        db.query(Recipe)
        .filter(
            Recipe.id == recipe_id,
            Recipe.user_id == current_user.id,
        )
        .first()
    )

    if not recipe:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found"
        )

    allowed_fields = [
        "title",
        "description",
        "cuisine",
        "diet",
        "language",
        "servings",
        "prep_time",
        "cook_time",
        "difficulty",
    ]

    for field in allowed_fields:
        if field in recipe_data:
            setattr(recipe, field, recipe_data[field])

    if "ingredients" in recipe_data:
        recipe.ingredients = json.dumps(
            recipe_data["ingredients"],
            ensure_ascii=False
        )

    if "instructions" in recipe_data:
        recipe.instructions = json.dumps(
            recipe_data["instructions"],
            ensure_ascii=False
        )

    if "nutrition" in recipe_data:
        recipe.nutrition = json.dumps(
            recipe_data["nutrition"],
            ensure_ascii=False
        )

    if not recipe.title:
        raise HTTPException(
            status_code=400,
            detail="title cannot be empty"
        )

    db.commit()
    db.refresh(recipe)

    return {
        "message": "Recipe updated successfully",
        "recipe": recipe_to_dict(recipe)
    }


@router.delete("/{recipe_id}")
def delete_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recipe = (
        db.query(Recipe)
        .filter(
            Recipe.id == recipe_id,
            Recipe.user_id == current_user.id,
        )
        .first()
    )

    if not recipe:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found"
        )

    db.delete(recipe)
    db.commit()

    return {
        "message": "Recipe deleted successfully",
        "recipe_id": recipe_id
    }
