from app.database import SessionLocal
from app.recipe_models import Recipe

db = SessionLocal()

recipe = Recipe(
    title="Test Tomato Rice",
    description="A simple test recipe for the V2 database.",
    cuisine="Indian",
    diet="Vegetarian",
    language="English",
    servings=2,
    prep_time=10,
    cook_time=20,
    difficulty="Easy",
    ingredients="Rice, Tomato, Onion, Oil, Salt",
    instructions="Cook rice. Saute onion and tomato. Mix with rice.",
    nutrition="Calories: 320 kcal"
)

db.add(recipe)
db.commit()

print("Test recipe inserted successfully")
db.close()
