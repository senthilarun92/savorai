from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.meal_plan_models import MealPlan
from app.models import User
from app.recipe_models import Recipe

router = APIRouter(prefix="/api/meal-planner", tags=["Meal Planner"])


@router.post("")
def add_meal_plan(data: dict, db: Session = Depends(get_db)):
    user_id = data.get("user_id")
    plan_date = data.get("plan_date")
    meal_type = data.get("meal_type")
    recipe_id = data.get("recipe_id")

    if not user_id or not plan_date or not meal_type:
        raise HTTPException(
            status_code=400,
            detail="user_id, plan_date and meal_type are required"
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if recipe_id:
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()

        if not recipe:
            raise HTTPException(
                status_code=404,
                detail="Recipe not found"
            )

    meal_plan = MealPlan(
        user_id=user_id,
        plan_date=plan_date,
        meal_type=meal_type,
        recipe_id=recipe_id
    )

    db.add(meal_plan)
    db.commit()
    db.refresh(meal_plan)

    return {
        "message": "Meal plan added successfully",
        "id": meal_plan.id,
        "user_id": meal_plan.user_id,
        "plan_date": meal_plan.plan_date,
        "meal_type": meal_plan.meal_type,
        "recipe_id": meal_plan.recipe_id
    }


@router.get("/{user_id}")
def get_meal_plans(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    meal_plans = (
        db.query(MealPlan, Recipe)
        .outerjoin(Recipe, MealPlan.recipe_id == Recipe.id)
        .filter(MealPlan.user_id == user_id)
        .order_by(MealPlan.plan_date.asc(), MealPlan.meal_type.asc())
        .all()
    )

    return [
        {
            "id": meal_plan.id,
            "plan_date": meal_plan.plan_date,
            "meal_type": meal_plan.meal_type,
            "recipe_id": meal_plan.recipe_id,
            "recipe_title": recipe.title if recipe else None
        }
        for meal_plan, recipe in meal_plans
    ]


@router.delete("/{user_id}/{meal_plan_id}")
def delete_meal_plan(
    user_id: int,
    meal_plan_id: int,
    db: Session = Depends(get_db)
):
    meal_plan = db.query(MealPlan).filter(
        MealPlan.id == meal_plan_id,
        MealPlan.user_id == user_id
    ).first()

    if not meal_plan:
        raise HTTPException(
            status_code=404,
            detail="Meal plan not found"
        )

    db.delete(meal_plan)
    db.commit()

    return {
        "message": "Meal plan deleted successfully",
        "user_id": user_id,
        "meal_plan_id": meal_plan_id
    }
