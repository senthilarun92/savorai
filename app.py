import os
import io
import re
import json
import base64
import time
from typing import Dict, Any, List, Optional
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from PIL import Image
import groq

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Ensure UTF-8 output in Flask JSON responses
app.json.ensure_ascii = False

# ==============================================================================
# CONFIGURATION
# ==============================================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.8-27b").strip()
GROQ_TEXT_MODEL = os.getenv("GROQ_TEXT_MODEL", "qwen/qwen3.8-27b").strip()

# Initialize Groq client safely
def get_groq_client() -> groq.Groq:
    """Returns an authenticated Groq client or raises ValueError."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or api_key == "your_groq_api_key_here":
        raise ValueError(
            "GROQ_API_KEY is not configured. Please set a valid GROQ_API_KEY in your .env file."
        )
    return groq.Groq(api_key=api_key, timeout=45.0)

# ==============================================================================
# IN-MEMORY CACHE (Prevents redundant Groq calls and saves rate limits)
# ==============================================================================
_cache_dishes: Dict[str, Any] = {}
_cache_recipes: Dict[str, Any] = {}

def get_cache_key(*args) -> str:
    """Creates a normalized cache key from arguments."""
    return ":".join(str(a).strip().lower() for a in args)

# ==============================================================================
# JSON EXTRACTION & PARSING UTILITY
# ==============================================================================
def parse_model_response(raw_text: str) -> Dict[str, Any]:
    """
    Robustly extracts and parses a JSON object from AI model text responses.
    Handles markdown code fences, trailing commas, and peripheral text.
    """
    if not raw_text or not isinstance(raw_text, str):
        raise ValueError("Empty or invalid response received from model.")

    clean = raw_text.strip()

    # Strip markdown code blocks like ```json ... ``` or ``` ... ```
    if "```" in clean:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean, re.IGNORECASE)
        if match:
            clean = match.group(1).strip()

    # Find boundaries of JSON object or array
    start_brace = clean.find("{")
    end_brace = clean.rfind("}")
    start_bracket = clean.find("[")
    end_bracket = clean.rfind("]")

    if start_brace != -1 and end_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
        json_str = clean[start_brace:end_brace + 1]
    elif start_bracket != -1 and end_bracket != -1:
        json_str = clean[start_bracket:end_bracket + 1]
    else:
        json_str = clean

    # Remove possible trailing commas before closing braces/brackets
    json_str_cleaned = re.sub(r",\s*([\]}])", r"\1", json_str)

    try:
        return json.loads(json_str_cleaned)
    except json.JSONDecodeError:
        # Fallback to direct json.loads on raw slice
        return json.loads(json_str)

# ==============================================================================
# DIET & CUISINE PROMPT ENHANCER
# ==============================================================================
def build_diet_rules(diet: str) -> str:
    """Builds strict diet constraints for chef system instructions."""
    normalized = diet.strip().lower()
    if normalized == "vegan":
        return (
            "STRICT DIET RULE - VEGAN:\n"
            "- Absolutely NO meat, poultry, beef, pork, chicken, fish, seafood, dairy "
            "(milk, butter, cheese, cream, yogurt, ghee), eggs, or animal honey.\n"
            "- Only plant-based ingredients (vegetables, grains, legumes, fruits, nuts, seeds, tofu, plant milks)."
        )
    if normalized == "vegetarian":
        return (
            "STRICT DIET RULE - VEGETARIAN:\n"
            "- Absolutely NO meat, poultry, beef, pork, chicken, fish, seafood, or animal gelatin.\n"
            "- Vegetarian dairy (paneer, milk, yogurt, butter) and plant ingredients are allowed."
        )
    if normalized == "high protein":
        return (
            "DIET RULE - HIGH PROTEIN:\n"
            "- Maximize and prioritize protein-dense ingredients (e.g., lentils, beans, chickpeas, "
            "paneer, eggs, chicken, fish, tofu, edamame, Greek yogurt depending on ingredients)."
        )
    if normalized == "keto":
        return (
            "STRICT DIET RULE - KETO / LOW CARB:\n"
            "- Strictly low-carbohydrate and high-healthy-fat.\n"
            "- Strictly avoid high-carb foods: white rice, potatoes, wheat flour, bread, pasta, sugar, corn."
        )
    if normalized == "gluten-free":
        return (
            "STRICT DIET RULE - GLUTEN-FREE:\n"
            "- Strictly avoid wheat, barley, rye, semolina, and wheat-based soy sauce."
        )
    return "Diet: Follow standard culinary balance."

# ==============================================================================
# ROUTES
# ==============================================================================

@app.route("/")
def home():
    """Serves the main application page."""
    return render_template("index.html")

@app.route("/suggest_dishes", methods=["POST"])
def suggest_dishes():
    """
    Generates 5 recipe suggestions based on provided ingredients, cuisine,
    dietary preference, and language.
    """
    try:
        data = request.get_json(silent=True) or {}

        ingredients = str(data.get("ingredients", "")).strip()
        cuisine = str(data.get("cuisine", "Any")).strip()
        diet = str(data.get("diet", "Any")).strip()
        language = str(data.get("language", "English")).strip()

        if not ingredients:
            return jsonify({
                "error": "Please enter or capture at least one ingredient."
            }), 400

        # Check in-memory cache
        cache_key = get_cache_key("dishes", ingredients, cuisine, diet, language)
        if cache_key in _cache_dishes:
            return jsonify(_cache_dishes[cache_key])

        client = get_groq_client()
        diet_instruction = build_diet_rules(diet)

        system_prompt = (
            f"You are a master executive chef AI specializing in personalized recipes.\n"
            f"{diet_instruction}\n"
            f"Cuisine Preference: {cuisine}\n"
            f"CRITICAL LANGUAGE REQUIREMENT: All recipe names and descriptions MUST be generated in the requested language: {language}.\n"
            f"Return ONLY a valid JSON object matching this schema:\n"
            f"{{\n"
            f'  "recipes": [\n'
            f'    {{"name": "Dish Name", "description": "Tasty 1-2 sentence appetizing description."}}\n'
            f'  ]\n'
            f"}}"
        )

        user_prompt = (
            f"Available Ingredients: {ingredients}\n"
            f"Desired Cuisine: {cuisine}\n"
            f"Dietary Restriction: {diet}\n"
            f"Output Language: {language}\n\n"
            f"Generate exactly 5 distinct, delicious recipe ideas utilizing these ingredients.\n"
            f"Ensure the diet restriction ({diet}) is 100% strictly followed."
        )

        completion = client.chat.completions.create(
            model=GROQ_TEXT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=1500
        )

        raw_result = completion.choices[0].message.content or ""
        parsed = parse_model_response(raw_result)

        # Ensure "recipes" key exists and is a list
        if "recipes" not in parsed or not isinstance(parsed["recipes"], list):
            # Sometimes models return a top-level list
            if isinstance(parsed, list):
                parsed = {"recipes": parsed}
            else:
                raise ValueError("Model did not return a valid list of recipes.")

        # Cache result
        _cache_dishes[cache_key] = parsed

        return jsonify(parsed)

    except groq.RateLimitError as rle:
        retry_msg = "Groq API rate limit reached. Please wait a few moments before trying again."
        return jsonify({"error": retry_msg, "rate_limited": True}), 429

    except groq.APIConnectionError:
        return jsonify({"error": "Unable to connect to AI service. Please check network connection."}), 503

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/generate_recipe", methods=["POST"])
def generate_recipe():
    """
    Generates complete cooking instructions, nutrition breakdown, ingredients,
    and chef tips for a specific chosen recipe.
    """
    try:
        data = request.get_json(silent=True) or {}

        dish_name = str(data.get("dish_name", "")).strip()
        cuisine = str(data.get("cuisine", "Any")).strip()
        diet = str(data.get("diet", "Any")).strip()
        language = str(data.get("language", "English")).strip()
        base_ingredients = str(data.get("ingredients", "")).strip()

        if not dish_name:
            return jsonify({"error": "Dish name is required."}), 400

        # Check in-memory cache
        cache_key = get_cache_key("recipe", dish_name, cuisine, diet, language)
        if cache_key in _cache_recipes:
            return jsonify(_cache_recipes[cache_key])

        client = get_groq_client()
        diet_instruction = build_diet_rules(diet)

        system_prompt = (
            f"You are a world-class professional culinary chef.\n"
            f"{diet_instruction}\n"
            f"Cuisine: {cuisine}\n"
            f"CRITICAL LANGUAGE RULE: The entire response — title, description, prep_time, cook_time, "
            f"difficulty, nutrition labels/values, ingredients with measurements, step-by-step instructions, "
            f"chef tips, and similar recipes — MUST be written in the specified language: {language}.\n"
            f"Return ONLY valid JSON matching this schema:\n"
            f"{{\n"
            f'  "recipe": {{\n'
            f'    "title": "Recipe Title",\n'
            f'    "description": "Appetizing description of the dish",\n'
            f'    "prep_time": "15 mins",\n'
            f'    "cook_time": "30 mins",\n'
            f'    "servings": 2,\n'
            f'    "difficulty": "Easy",\n'
            f'    "nutrition": {{\n'
            f'      "calories": "350 kcal",\n'
            f'      "protein": "15g",\n'
            f'      "carbs": "40g",\n'
            f'      "fat": "10g"\n'
            f'    }},\n'
            f'    "ingredients": ["Quantity + Ingredient 1", "Quantity + Ingredient 2"],\n'
            f'    "instructions": ["Step 1 detailed instructions", "Step 2 detailed instructions"],\n'
            f'    "tips": "Practical chef tip for maximum flavor or best result",\n'
            f'    "similar": ["Similar Dish 1", "Similar Dish 2"]\n'
            f'  }}\n'
            f"}}"
        )

        user_prompt = (
            f"Dish to prepare: {dish_name}\n"
            f"Cuisine style: {cuisine}\n"
            f"Diet requirement: {diet}\n"
            f"Base available ingredients: {base_ingredients or 'Standard kitchen staples'}\n"
            f"Language: {language}\n\n"
            f"Provide the complete, step-by-step master chef recipe."
        )

        completion = client.chat.completions.create(
            model=GROQ_TEXT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=3000
        )

        raw_result = completion.choices[0].message.content or ""
        parsed = parse_model_response(raw_result)

        if "recipe" not in parsed:
            raise ValueError("Model response did not contain recipe details.")

        # Cache result
        _cache_recipes[cache_key] = parsed

        return jsonify(parsed)

    except groq.RateLimitError:
        return jsonify({
            "error": "Groq API rate limit reached. Please wait a few moments before trying again.",
            "rate_limited": True
        }), 429

    except groq.APIConnectionError:
        return jsonify({"error": "Unable to connect to AI service. Please check network connection."}), 503

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/analyze_image", methods=["POST"])
def analyze_image():
    """
    Receives a camera-captured photo or uploaded image, optimizes it, and uses
    Groq's vision model to accurately identify visible raw food ingredients.
    """
    try:
        image_data_uri = None

        # Check JSON payload for base64 data URI
        if request.is_json:
            data = request.get_json() or {}
            image_data_uri = data.get("image")

        # Check multipart form data upload
        elif "image" in request.files:
            file = request.files["image"]
            if file and file.filename != "":
                raw_bytes = file.read()
                b64 = base64.b64encode(raw_bytes).decode("utf-8")
                mime = file.mimetype or "image/jpeg"
                image_data_uri = f"data:{mime};base64,{b64}"

        if not image_data_uri:
            return jsonify({"error": "No image data provided. Please capture or upload a photo."}), 400

        # Validate and process base64 data
        match = re.match(r"^data:(image\/[a-zA-Z0-9\+\-\.]+);base64,(.+)$", image_data_uri)
        if match:
            b64_str = match.group(2)
        else:
            b64_str = image_data_uri

        try:
            image_bytes = base64.b64decode(b64_str)
            img = Image.open(io.BytesIO(image_bytes))
        except Exception:
            return jsonify({"error": "Invalid image format received."}), 400

        # Ensure image is RGB (convert RGBA/palette)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Verify minimum dimensions required by Groq API (at least 32x32)
        width, height = img.size
        if width < 32 or height < 32:
            img = img.resize((max(width, 32), max(height, 32)), Image.Resampling.LANCZOS)

        # Optimize size: max 1024 on longest edge to minimize latency and token size
        max_dimension = 1024
        if width > max_dimension or height > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        # Compress to high-efficiency JPEG
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=82, optimize=True)
        optimized_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        clean_data_uri = f"data:image/jpeg;base64,{optimized_b64}"

        client = get_groq_client()

        system_prompt = (
            "You are an expert culinary vision assistant.\n"
            "Examine the image carefully and identify ONLY the visible raw food ingredients, vegetables, "
            "fruits, groceries, herbs, spices, pantry items, dairy, or meats that can be used for cooking.\n\n"
            "STRICT RULES:\n"
            "1. Identify ONLY food items that are clearly and reasonably visible.\n"
            "2. Do NOT guess, imagine, or hallucinate ingredients that are not in the picture.\n"
            "3. If no food ingredients or groceries are visible, return an empty array for ingredients.\n"
            "4. Output simple, concise culinary ingredient names (e.g. ['tomato', 'onion', 'garlic', 'potato']).\n"
            "5. Return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            '  "ingredients": ["ingredient1", "ingredient2"],\n'
            '  "message": "Found 2 ingredients: ingredient1, ingredient2."\n'
            "}"
        )

        user_content = [
            {
                "type": "text",
                "text": "Identify all visible food ingredients in this photo for cooking recipes."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": clean_data_uri
                }
            }
        ]

        completion = client.chat.completions.create(
            model=GROQ_VISION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=300
        )

        raw_result = completion.choices[0].message.content or ""
        parsed = parse_model_response(raw_result)

        ingredients_list = parsed.get("ingredients", [])
        if not isinstance(ingredients_list, list):
            ingredients_list = []

        # Sanitize and deduplicate
        cleaned_ingredients = []
        seen = set()
        for item in ingredients_list:
            if isinstance(item, str):
                cleaned = item.strip().lower()
                if cleaned and cleaned not in seen:
                    seen.add(cleaned)
                    cleaned_ingredients.append(cleaned)

        message = parsed.get("message")
        if not message:
            if cleaned_ingredients:
                message = f"Detected {len(cleaned_ingredients)} ingredient(s): {', '.join(cleaned_ingredients)}."
            else:
                message = "No food ingredients were clearly identified. Please take a clearer photo or add ingredients manually."

        return jsonify({
            "ingredients": cleaned_ingredients,
            "message": message
        })

    except groq.RateLimitError:
        return jsonify({
            "error": "Groq Vision API rate limit reached. Please wait a moment before trying again.",
            "rate_limited": True
        }), 429

    except groq.APIConnectionError:
        return jsonify({"error": "Unable to connect to AI vision service. Please check network connection."}), 503

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def find_available_port(preferred_port: int = 5001) -> int:
    """Finds an available TCP port starting from preferred_port."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", preferred_port)) != 0:
            return preferred_port
    for p in range(preferred_port + 1, preferred_port + 30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return preferred_port


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
if __name__ == "__main__":
    configured_port = int(os.getenv("PORT", "5001"))
    port = find_available_port(configured_port)
    print(f"Starting AI Food Recipe & Camera Chef on http://127.0.0.1:{port}")
    app.run(
        host="127.0.0.1",
        port=port,
        debug=True,
        use_reloader=False
    )
