from pydantic import BaseModel
from typing import List


class RecipeIngredient(BaseModel):
    name: str
    quantity: str


class RecipeNutrition(BaseModel):
    calories: str
    protein: str
    carbs: str
    fat: str


class RecipeResponse(BaseModel):
    title: str
    description: str
    servings: int
    prep_time: int
    cook_time: int
    difficulty: str
    ingredients: List[RecipeIngredient]
    instructions: List[str]
    nutrition: RecipeNutrition
    chef_tips: List[str]
