import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import parse_model_response


class TestParseModelResponse(unittest.TestCase):
    def test_extracts_json_from_clean_string(self):
        sample = '{"recipes": [{"name": "Tomato Soup", "description": "Classic comforting soup"}]}'
        result = parse_model_response(sample)
        self.assertEqual(result["recipes"][0]["name"], "Tomato Soup")
        self.assertEqual(result["recipes"][0]["description"], "Classic comforting soup")

    def test_extracts_json_from_markdown_code_block(self):
        sample = '''
Here is the recipe suggestions list:
```json
{
  "recipes": [
    {
      "name": "Paneer Butter Masala",
      "description": "Rich and creamy curry with fresh paneer cubes."
    }
  ]
}
```
Enjoy cooking!
'''
        result = parse_model_response(sample)
        self.assertIn("recipes", result)
        self.assertEqual(result["recipes"][0]["name"], "Paneer Butter Masala")

    def test_extracts_json_without_json_tag_in_code_block(self):
        sample = '''
```
{
  "ingredients": ["tomato", "onion", "garlic"],
  "message": "Found 3 ingredients"
}
```
'''
        result = parse_model_response(sample)
        self.assertEqual(result["ingredients"], ["tomato", "onion", "garlic"])
        self.assertEqual(result["message"], "Found 3 ingredients")

    def test_handles_trailing_commas_gracefully(self):
        sample = '''
{
  "recipe": {
    "title": "Vegetable Stir Fry",
    "ingredients": [
      "broccoli",
      "bell pepper",
    ],
  }
}
'''
        result = parse_model_response(sample)
        self.assertEqual(result["recipe"]["title"], "Vegetable Stir Fry")
        self.assertEqual(result["recipe"]["ingredients"], ["broccoli", "bell pepper"])

    def test_raises_error_for_empty_or_non_json_string(self):
        with self.assertRaises(ValueError):
            parse_model_response("")

        with self.assertRaises(Exception):
            parse_model_response("There is no JSON in this text at all.")


if __name__ == "__main__":
    unittest.main()
