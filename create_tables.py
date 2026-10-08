from app.database import engine, Base
from app.models import User
from app.recipe_models import Recipe
from app.saved_recipe_models import SavedRecipe
from app.pantry_models import PantryItem
from app.shopping_models import ShoppingItem
from app.meal_plan_models import MealPlan

Base.metadata.create_all(bind=engine)

print("Meal plans table created successfully")
