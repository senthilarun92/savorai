import unittest
import json
import base64
import io
import sys
import os
from PIL import Image, ImageDraw

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app


class TestLiveApiEndpoints(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_live_suggest_dishes(self):
        payload = {
            "ingredients": "bell pepper, tofu, soy sauce, garlic",
            "cuisine": "Chinese",
            "diet": "Vegan",
            "language": "English"
        }
        response = self.app.post(
            "/suggest_dishes",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, f"Failed with {response.data}")
        data = json.loads(response.data)
        self.assertIn("recipes", data)
        self.assertIsInstance(data["recipes"], list)
        self.assertGreaterEqual(len(data["recipes"]), 1)
        first_recipe = data["recipes"][0]
        self.assertIn("name", first_recipe)
        self.assertIn("description", first_recipe)
        print(f"\n[LIVE TEST] Dish suggestion success: '{first_recipe['name']}'")

    def test_live_generate_recipe(self):
        payload = {
            "dish_name": "Garlic Tofu Stir Fry",
            "cuisine": "Chinese",
            "diet": "Vegan",
            "language": "English",
            "ingredients": "tofu, garlic, soy sauce"
        }
        response = self.app.post(
            "/generate_recipe",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, f"Failed with {response.data}")
        data = json.loads(response.data)
        self.assertIn("recipe", data)
        recipe = data["recipe"]
        self.assertIn("title", recipe)
        self.assertIn("ingredients", recipe)
        self.assertIn("instructions", recipe)
        self.assertIn("nutrition", recipe)
        print(f"\n[LIVE TEST] Full recipe generation success: '{recipe['title']}'")

    def test_live_tamil_suggestions(self):
        payload = {
            "ingredients": "tomato, onion, mustard seeds, curry leaves",
            "cuisine": "Indian",
            "diet": "Vegetarian",
            "language": "Tamil"
        }
        response = self.app.post(
            "/suggest_dishes",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, f"Failed with {response.data}")
        data = json.loads(response.data)
        self.assertIn("recipes", data)
        self.assertGreaterEqual(len(data["recipes"]), 1)
        first_recipe = data["recipes"][0]
        self.assertIn("name", first_recipe)
        safe_name = first_recipe['name'].encode('ascii', 'backslashreplace').decode('ascii')
        print(f"\n[LIVE TEST] Tamil suggestion success: {safe_name}")

    def test_live_analyze_image(self):
        # Create a test image with a drawing of a tomato
        img = Image.new("RGB", (150, 150), color=(245, 245, 245))
        draw = ImageDraw.Draw(img)
        draw.ellipse((30, 45, 120, 135), fill=(220, 30, 20)) # Red circle
        draw.polygon([(75, 20), (65, 48), (85, 48)], fill=(34, 139, 34)) # Green stem

        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        data_uri = f"data:image/jpeg;base64,{b64}"

        response = self.app.post(
            "/analyze_image",
            data=json.dumps({"image": data_uri}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, f"Failed with {response.data}")
        data = json.loads(response.data)
        self.assertIn("ingredients", data)
        self.assertIn("message", data)
        print(f"\n[LIVE TEST] Vision image analysis success: {data['ingredients']}")


if __name__ == "__main__":
    unittest.main()
