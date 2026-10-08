import unittest
import json
import base64
import io
import sys
import os
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app, build_diet_rules, get_cache_key


class TestAppRoutes(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_home_page_loads(self):
        response = self.app.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"AI Recipe Generator", response.data)
        self.assertIn(b"Camera", response.data)
        self.assertIn(b"Voice Input", response.data)

    def test_suggest_dishes_requires_ingredients(self):
        response = self.app.post(
            "/suggest_dishes",
            data=json.dumps({"ingredients": ""}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_generate_recipe_requires_dish_name(self):
        response = self.app.post(
            "/generate_recipe",
            data=json.dumps({"dish_name": ""}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_analyze_image_requires_image(self):
        response = self.app.post(
            "/analyze_image",
            data=json.dumps({}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_analyze_image_rejects_corrupted_image(self):
        response = self.app.post(
            "/analyze_image",
            data=json.dumps({"image": "data:image/jpeg;base64,invalid_corrupt_data"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_build_diet_rules_vegan(self):
        rules = build_diet_rules("Vegan")
        self.assertIn("STRICT DIET RULE - VEGAN", rules)
        self.assertIn("NO meat", rules)
        self.assertIn("dairy", rules)

    def test_build_diet_rules_vegetarian(self):
        rules = build_diet_rules("Vegetarian")
        self.assertIn("STRICT DIET RULE - VEGETARIAN", rules)
        self.assertIn("NO meat", rules)

    def test_build_diet_rules_keto(self):
        rules = build_diet_rules("Keto")
        self.assertIn("KETO", rules)
        self.assertIn("low-carbohydrate", rules)

    def test_cache_key_generation(self):
        key1 = get_cache_key("dishes", "Tomato, Onion", "Indian", "Vegetarian", "English")
        key2 = get_cache_key("dishes", "tomato, onion", "indian", "vegetarian", "english")
        self.assertEqual(key1, key2)


if __name__ == "__main__":
    unittest.main()
