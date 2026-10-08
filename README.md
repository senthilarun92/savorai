# 🍳 AI Food Recipe Generator & Camera Chef

An intelligent culinary application powered by **Groq** and **Qwen Multimodal AI (`qwen/qwen3.8-27b`)**. Snap a photo of vegetables and groceries to auto-detect ingredients, speak your pantry items with voice recognition, or type them manually to instantly generate 5 tailored recipes and detailed step-by-step master chef guides in English, Tamil, Hindi, French, and more.

---

## ✨ Features

- **📷 Camera-Based Ingredient Detection (NEW)**:
  - Browser-native live camera viewfinder using `navigator.mediaDevices.getUserMedia()`.
  - Capture photos of vegetables, fruits, groceries, or pantry items.
  - Client-side image optimization (resizing & compression) to minimize latency and token consumption.
  - Powered by Groq's multimodal `qwen/qwen3.8-27b` vision model.
  - Returns structured, verified food ingredients with interactive chips (add, remove, or replace into the ingredients field).
  - Alternative file upload fallback for devices without webcams or when permissions are restricted.

- **🎤 Voice Input**:
  - Hands-free voice recognition using the Web Speech API.
  - Automatically matches speech recognition locale to the selected output language (e.g., `ta-IN`, `hi-IN`, `en-US`, `fr-FR`).
  - Visual pulsing indicator and graceful fallback when unsupported.

- **✍️ Manual Ingredient Input & Editing**:
  - Full freedom to edit, combine, add, or refine ingredients before generating recipes.
  - Quick sample presets for testing (e.g. Pasta, Curry).

- **🌍 Multilingual Recipe Generation**:
  - Complete native generation in **English**, **Tamil (தமிழ்)**, **Hindi (हिन्दी)**, **French (Français)**, **Spanish**, **German**, and **Italian**.
  - All dish titles, descriptions, prep/cook times, difficulty ratings, nutrition metrics, ingredients, step-by-step instructions, and chef tips are translated into the chosen language.

- **🥗 Diet & Cuisine Customization**:
  - **Diets**: Any, Vegetarian, Vegan, High Protein, Keto, Gluten-Free, Dairy-Free.
  - Strict diet rules enforced (e.g., Vegan strictly excludes all meats, seafood, dairy, eggs, and animal honey; Keto eliminates high-carb foods like grains, potatoes, and sugars).
  - **Cuisines**: Indian, Italian, Chinese, Mexican, Mediterranean, Japanese, Thai, French, Spanish, American.

- **🍽️ Two-Tier Recipe Workflow**:
  1. **5 Recipe Ideas**: Overview cards with dish names and mouth-watering descriptions.
  2. **Complete Culinary Guide**: Click any card to generate the full recipe with:
     - Servings, Prep Time, Cook Time, Difficulty
     - Complete Nutrition Breakdown (Calories, Protein, Carbs, Fat)
     - Interactive checklist of ingredients with quantities
     - Numbered step-by-step cooking instructions
     - Chef's secret flavor tip
     - Similar dish recommendations (clickable to generate instantly)
     - Print-ready recipe view

- **🌓 Theme Switching**:
  - Full Dark Mode and Light Mode with persistent preference in `localStorage`.

- **🛡️ Rate Limit & Security Design**:
  - In-memory response caching to prevent redundant AI queries and protect Groq API rate limits.
  - Sensible timeouts and friendly HTTP 429 rate-limit handling.
  - Zero API key exposure to the browser (all Groq calls reside on the Python Flask backend).

---

## 📁 Project Structure

```
ai_food_camera_recipe/
│
├── app.py                  # Flask backend & Groq API controller
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
├── .env                    # Local environment variables (Groq API Key)
├── .env.example            # Environment variables template
├── .gitignore              # Git ignore rules
│
├── templates/
│   └── index.html          # Semantic HTML5 frontend template with camera modal
│
├── static/
│   ├── style.css           # Responsive design, light/dark themes, animations
│   └── app.js              # Camera capture, voice recognition, recipe logic
│
└── tests/
    ├── __init__.py
    ├── test_json_parser.py # Tests for robust model response parsing
    ├── test_routes.py      # Tests for Flask endpoints and validations
    └── test_live_api.py    # Integration tests against live Groq endpoints
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- A Groq API key from [Groq Console](https://console.groq.com/keys)

### 2. Installation
Clone or navigate to the project directory:
```bash
cd ai_food_camera_recipe
```

Install the required Python packages:
```bash
pip install -r requirements.txt
```

### 3. Configuration
Copy `.env.example` to `.env` (or update existing `.env`):
```bash
cp .env.example .env
```
Ensure your `.env` contains:
```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_VISION_MODEL=qwen/qwen3.8-27b
GROQ_TEXT_MODEL=qwen/qwen3.8-27b
PORT=5000
```

### 4. Running the Application
Start the Flask development server:
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🧪 Running Tests

Execute all unit and route validation tests:
```bash
python -m unittest discover tests
```

Execute live Groq API tests:
```bash
python -m unittest tests/test_live_api.py
```

---

## 🔒 Security & Best Practices
- Never commit `.env` or hardcode API keys.
- Camera access requires user permission and all media streams are stopped when the modal closes.
- Image uploads are bounded in size and compressed on the client before transmission.
