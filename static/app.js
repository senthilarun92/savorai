/**
 * AI FOOD RECIPE GENERATOR & CAMERA CHEF
 * Frontend Application Controller
 */

// ==============================================================================
// APPLICATION STATE
// ==============================================================================
const state = {
    cameraStream: null,
    currentFacingMode: "environment", // Default to back camera on mobile
    capturedImageDataUri: null,
    detectedIngredients: [],
    speechRecognition: null,
    isVoiceListening: false,
    voiceUserRequestedStop: false,
    voiceIsStarting: false,
    voiceRestartTimeout: null,
    voiceLastProcessedIndex: -1,
    isGenerating: false,
    selectedDishName: null,
    currentUser: null,
    isAuthenticated: false
};

// ==============================================================================
// INITIALIZATION
// ==============================================================================
document.addEventListener("DOMContentLoaded", () => {
    initTheme();
});

// ==============================================================================
// THEME MANAGEMENT
// ==============================================================================
function initTheme() {
    const savedTheme = localStorage.getItem("app_theme") || "dark";
    if (savedTheme === "light") {
        document.body.classList.remove("dark-theme");
        document.body.classList.add("light-theme");
        updateThemeUI("light");
    } else {
        document.body.classList.remove("light-theme");
        document.body.classList.add("dark-theme");
        updateThemeUI("dark");
    }
}

function toggleTheme() {
    const isDark = document.body.classList.contains("dark-theme");
    if (isDark) {
        document.body.classList.remove("dark-theme");
        document.body.classList.add("light-theme");
        localStorage.setItem("app_theme", "light");
        updateThemeUI("light");
    } else {
        document.body.classList.remove("light-theme");
        document.body.classList.add("dark-theme");
        localStorage.setItem("app_theme", "dark");
        updateThemeUI("dark");
    }
}

function updateThemeUI(theme) {
    const icon = document.getElementById("themeIcon");
    const label = document.getElementById("themeLabel");
    const button = document.getElementById("themeToggleBtn");

    if (!icon || !label) return;

    if (theme === "light") {
        icon.innerHTML = `
            <svg viewBox="0 0 24 24"
                 aria-hidden="true"
                 focusable="false">
                <circle cx="12" cy="12" r="4"></circle>
                <path d="M12 2v2"></path>
                <path d="M12 20v2"></path>
                <path d="M4.93 4.93l1.41 1.41"></path>
                <path d="M17.66 17.66l1.41 1.41"></path>
                <path d="M2 12h2"></path>
                <path d="M20 12h2"></path>
                <path d="M4.93 19.07l1.41-1.41"></path>
                <path d="M17.66 6.34l1.41-1.41"></path>
            </svg>
        `;

        label.textContent = "Light";

        if (button) {
            button.setAttribute("aria-label", "Switch to dark theme");
            button.setAttribute("title", "Switch to dark theme");
        }
    } else {
        icon.innerHTML = `
            <svg viewBox="0 0 24 24"
                 aria-hidden="true"
                 focusable="false">
                <path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5
                         8.6 8.6 0 1 0 20.5 14.2Z"></path>
            </svg>
        `;

        label.textContent = "Dark";

        if (button) {
            button.setAttribute("aria-label", "Switch to light theme");
            button.setAttribute("title", "Switch to light theme");
        }
    }
}

// ==============================================================================
// ERROR & LOADER HANDLING
// ==============================================================================
function showError(message) {
    const errorBox = document.getElementById("errorBox");
    const errorMessage = document.getElementById("errorMessage");
    if (errorBox && errorMessage) {
        errorMessage.innerText = message;
        errorBox.style.display = "flex";
        errorBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
}

function hideError() {
    const errorBox = document.getElementById("errorBox");
    if (errorBox) {
        errorBox.style.display = "none";
    }
}

function showLoader(title = "Cooking up recipes...", subtitle = "Our AI chef is crafting delicious culinary suggestions.") {
    const loader = document.getElementById("loader");
    const loaderTitle = document.getElementById("loaderTitle");
    const loaderSubtitle = document.getElementById("loaderSubtitle");

    if (loader) {
        if (loaderTitle) loaderTitle.innerText = title;
        if (loaderSubtitle) loaderSubtitle.innerText = subtitle;
        loader.style.display = "block";
        loader.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}

function hideLoader() {
    const loader = document.getElementById("loader");
    if (loader) {
        loader.style.display = "none";
    }
}

// Quick Sample Helpers
function clearIngredients() {
    const ingredients = document.getElementById("ingredients");
    if (ingredients) {
        ingredients.value = "";
        ingredients.focus();
    }
}

function insertSample(type) {
    const ingredients = document.getElementById("ingredients");
    const cuisine = document.getElementById("cuisine");
    const diet = document.getElementById("diet");

    if (type === "pasta") {
        ingredients.value = "penne pasta, ripe tomatoes, garlic, basil, olive oil, parmesan cheese";
        cuisine.value = "Italian";
        diet.value = "Vegetarian";
    } else if (type === "curry") {
        ingredients.value = "paneer, onions, tomatoes, ginger, garlic, garam masala, turmeric, cumin";
        cuisine.value = "Indian";
        diet.value = "Vegetarian";
    }
}

function onLanguageChange() {
    // If voice recognition is active, update language
    if (state.isVoiceListening && state.speechRecognition) {
        stopVoiceInput();
    }
}

// ==============================================================================
// VOICE INPUT FUNCTIONALITY & COMPOUND TOKENIZER
// ==============================================================================
const compoundPrefixes = new Set([
    'red', 'green', 'yellow', 'white', 'black', 'brown', 'sweet', 'hot', 'dry',
    'fresh', 'raw', 'spring', 'bell', 'chili', 'chilli', 'olive', 'sesame',
    'coconut', 'mustard', 'sunflower', 'vegetable', 'soy', 'soya', 'fish',
    'curry', 'bay', 'coriander', 'mint', 'baking', 'sour', 'cream', 'cottage',
    'cheddar', 'parmesan', 'extra', 'virgin', 'whole', 'crushed', 'ground',
    'garlic', 'ginger'
]);

const compoundSuffixes = new Set([
    'onion', 'onions', 'pepper', 'peppers', 'chilli', 'chillies', 'chili', 'oil',
    'sauce', 'leaves', 'leaf', 'milk', 'cheese', 'powder', 'paste', 'seeds',
    'seed', 'flour', 'beans', 'rice', 'vinegar', 'sugar', 'salt', 'butter'
]);

function parseSpokenIngredients(transcript) {
    if (!transcript || typeof transcript !== 'string') return [];

    // Normalize and clean punctuation, conjunctions
    const clean = transcript
        .toLowerCase()
        .replace(/[.!?;:]/g, ' ')
        .replace(/\band\b/g, ',')
        .replace(/&/g, ',');

    // Split on commas first
    const rawSegments = clean.split(',').map(s => s.trim()).filter(Boolean);
    const results = [];

    for (const segment of rawSegments) {
        const words = segment.split(/\s+/).filter(Boolean);
        if (words.length <= 1) {
            if (words.length === 1) results.push(words[0]);
            continue;
        }

        let i = 0;
        while (i < words.length) {
            const current = words[i];
            const next = words[i + 1];
            const nextNext = words[i + 2];

            // 4-word compound: "extra virgin olive oil"
            if (current === 'extra' && next === 'virgin' && nextNext === 'olive' && words[i + 3] === 'oil') {
                results.push('extra virgin olive oil');
                i += 4;
            }
            // 2-word compound: prefix + suffix e.g. "red onion", "bell pepper", "olive oil"
            else if (next && compoundPrefixes.has(current) && compoundSuffixes.has(next)) {
                results.push(`${current} ${next}`);
                i += 2;
            }
            // 2-word paste: "garlic paste", "ginger paste"
            else if (next && (current === 'garlic' || current === 'ginger') && next === 'paste') {
                results.push(`${current} ${next}`);
                i += 2;
            }
            else {
                results.push(current);
                i++;
            }
        }
    }

    return results;
}

function addRecognizedIngredients(transcript) {
    const ingredientsField = document.getElementById("ingredients");
    if (!ingredientsField) return;

    const currentVal = ingredientsField.value.trim();
    const existingItems = currentVal
        ? currentVal.split(',').map(s => s.trim()).filter(Boolean)
        : [];

    const existingNormalized = new Set(existingItems.map(s => s.toLowerCase()));
    const newTokens = parseSpokenIngredients(transcript);
    const toAdd = [];

    for (const token of newTokens) {
        const norm = token.toLowerCase();
        if (!existingNormalized.has(norm)) {
            existingNormalized.add(norm);
            toAdd.push(token);
        }
    }

    if (toAdd.length > 0) {
        if (existingItems.length > 0) {
            ingredientsField.value = `${existingItems.join(', ')}, ${toAdd.join(', ')}`;
        } else {
            ingredientsField.value = toAdd.join(', ');
        }
    }
}

function getLanguageLocale(language) {
    if (!language) return "en-US";
    switch (language.toLowerCase()) {
        case "tamil": return "ta-IN";
        case "hindi": return "hi-IN";
        case "french": return "fr-FR";
        case "spanish": return "es-ES";
        case "german": return "de-DE";
        case "italian": return "it-IT";
        default: return "en-US";
    }
}

function updateVoiceUI(isListening) {
    const voiceBtn = document.getElementById("btnVoice");
    const voiceBanner = document.getElementById("voiceBanner");
    const voiceIcon = document.getElementById("voiceIcon");
    const voiceText = document.getElementById("voiceText");

    if (isListening) {
        if (voiceBanner) voiceBanner.style.display = "flex";
        if (voiceBtn) voiceBtn.classList.add("active");

        if (voiceText) voiceText.innerText = "Listening...";
    } else {
        if (voiceBanner) voiceBanner.style.display = "none";
        if (voiceBtn) voiceBtn.classList.remove("active");

        if (voiceText) voiceText.innerText = "Voice Input";
    }
}

function handleVoiceError(error) {
    let friendlyMessage = "";
    switch (error) {
        case "no-speech":
            // Quiet in continuous mode - user is pausing or thinking
            return;
        case "aborted":
            // Expected on user stop
            return;
        case "not-allowed":
            friendlyMessage = "Microphone access was denied. Please allow microphone permissions in your browser.";
            break;
        case "service-not-allowed":
            friendlyMessage = "Speech recognition service is not permitted by your browser or operating system.";
            break;
        case "audio-capture":
            friendlyMessage = "No microphone found or audio capture failed. Please check your microphone.";
            break;
        case "network":
            friendlyMessage = "Speech recognition network error. Please check your internet connection.";
            break;
        case "language-not-supported":
            friendlyMessage = "The selected language is not supported for speech recognition on this device.";
            break;
        default:
            friendlyMessage = "Voice recognition encountered an issue. You can continue typing manually.";
            break;
    }
    if (friendlyMessage) {
        showError(friendlyMessage);
    }
}

function createRecognitionInstance() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return null;

    const recognition = new SpeechRecognition();
    const currentLang = document.getElementById("language").value || "English";
    recognition.lang = getLanguageLocale(currentLang);
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
        state.voiceIsStarting = false;
        state.isVoiceListening = true;
        state.voiceLastProcessedIndex = -1;
        updateVoiceUI(true);
    };

    recognition.onresult = (event) => {
        // Process only newly received final speech results
        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (i <= state.voiceLastProcessedIndex) continue;
            const result = event.results[i];
            if (result && result.isFinal) {
                state.voiceLastProcessedIndex = i;
                const transcript = result[0] ? result[0].transcript : '';
                if (transcript && transcript.trim()) {
                    addRecognizedIngredients(transcript.trim());
                }
            }
        }
    };

    recognition.onerror = (event) => {
        console.warn("Speech recognition error:", event.error);
        if (event.error === "no-speech" || event.error === "aborted") {
            return;
        }
        if (event.error === "not-allowed" || event.error === "service-not-allowed" || event.error === "audio-capture") {
            state.voiceUserRequestedStop = true;
        }
        handleVoiceError(event.error);
        stopVoiceInput();
    };

    recognition.onend = () => {
        state.voiceIsStarting = false;
        if (state.voiceUserRequestedStop) {
            state.isVoiceListening = false;
            updateVoiceUI(false);
            state.speechRecognition = null;
        } else {
            // Unexpected disconnection: restart safely if user still expects to listen
            if (state.isVoiceListening && !state.voiceUserRequestedStop) {
                state.voiceRestartTimeout = setTimeout(() => {
                    if (state.isVoiceListening && !state.voiceUserRequestedStop) {
                        safeStartRecognition();
                    }
                }, 300);
            } else {
                state.isVoiceListening = false;
                updateVoiceUI(false);
                state.speechRecognition = null;
            }
        }
    };

    return recognition;
}

function safeStartRecognition() {
    if (state.speechRecognition) {
        const oldRec = state.speechRecognition;
        state.speechRecognition = null;
        oldRec.onstart = null;
        oldRec.onresult = null;
        oldRec.onerror = null;
        oldRec.onend = null;
        try { oldRec.abort(); } catch (e) {}
    }

    try {
        const recognition = createRecognitionInstance();
        if (!recognition) return;
        state.speechRecognition = recognition;
        state.voiceLastProcessedIndex = -1;
        recognition.start();
    } catch (err) {
        console.warn("Recognition start error:", err);
        stopVoiceInput();
    }
}

function toggleVoiceInput() {
    if (state.isVoiceListening || state.voiceIsStarting) {
        stopVoiceInput();
    } else {
        startVoiceInput();
    }
}

function startVoiceInput() {
    hideError();

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        showError("Voice recognition is not supported in this browser. Please use Chrome, Edge, or input ingredients manually.");
        return;
    }

    // Prevent duplicate starts
    if (state.voiceIsStarting || state.isVoiceListening) {
        return;
    }

    state.voiceIsStarting = true;
    state.voiceUserRequestedStop = false;
    state.voiceLastProcessedIndex = -1;

    if (state.voiceRestartTimeout) {
        clearTimeout(state.voiceRestartTimeout);
        state.voiceRestartTimeout = null;
    }

    safeStartRecognition();
}

function stopVoiceInput() {
    state.voiceUserRequestedStop = true;
    state.isVoiceListening = false;
    state.voiceIsStarting = false;

    if (state.voiceRestartTimeout) {
        clearTimeout(state.voiceRestartTimeout);
        state.voiceRestartTimeout = null;
    }

    if (state.speechRecognition) {
        const rec = state.speechRecognition;
        state.speechRecognition = null;
        rec.onstart = null;
        rec.onresult = null;
        rec.onerror = null;
        rec.onend = null;
        try {
            rec.stop();
        } catch (e) {
            // Ignore error on stop
        }
    }

    updateVoiceUI(false);
}

// ==============================================================================
// CAMERA-BASED INGREDIENT DETECTION
// ==============================================================================
function openCameraModal() {
    hideError();
    const modal = document.getElementById("cameraModal");
    if (modal) {
        modal.style.display = "flex";
        resetCameraModalUI();
        startCameraStream();
    }
}

function closeCameraModal() {
    stopCameraStream();
    const modal = document.getElementById("cameraModal");
    if (modal) {
        modal.style.display = "none";
    }
}

function resetCameraModalUI() {
    const video = document.getElementById("cameraVideo");
    const capturedPreview = document.getElementById("capturedImagePreview");
    const frame = document.getElementById("viewfinderFrame");
    const btnCapture = document.getElementById("btnCapturePhoto");
    const btnRetake = document.getElementById("btnRetakePhoto");
    const btnAnalyze = document.getElementById("btnAnalyzeImage");
    const cameraError = document.getElementById("cameraError");
    const detectedSection = document.getElementById("detectedSection");
    const cameraLoader = document.getElementById("cameraLoader");

    if (video) video.style.display = "block";
    if (capturedPreview) capturedPreview.style.display = "none";
    if (frame) frame.style.display = "block";
    if (btnCapture) btnCapture.style.display = "inline-flex";
    if (btnRetake) btnRetake.style.display = "none";
    if (btnAnalyze) btnAnalyze.style.display = "none";
    if (cameraError) cameraError.style.display = "none";
    if (detectedSection) detectedSection.style.display = "none";
    if (cameraLoader) cameraLoader.style.display = "none";

    state.capturedImageDataUri = null;
    state.detectedIngredients = [];
}

async function startCameraStream() {
    stopCameraStream();

    const video = document.getElementById("cameraVideo");
    const cameraError = document.getElementById("cameraError");
    const cameraErrorMessage = document.getElementById("cameraErrorMessage");

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        if (cameraError && cameraErrorMessage) {
            cameraErrorMessage.innerText = "Camera API is not supported in this browser. Please use 'Upload Photo' or type ingredients.";
            cameraError.style.display = "flex";
        }
        return;
    }

    try {
        const constraints = {
            video: {
                facingMode: state.currentFacingMode,
                width: { ideal: 1280 },
                height: { ideal: 720 }
            },
            audio: false
        };

        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        state.cameraStream = stream;

        if (video) {
            video.srcObject = stream;
            await video.play();
        }

        if (cameraError) cameraError.style.display = "none";

    } catch (err) {
        console.warn("Camera access error:", err);
        let msg = "Camera permission was denied or device not found. You can use 'Upload Photo' or enter ingredients manually.";
        if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
            msg = "Camera permission was denied. Please allow camera permissions in your browser or use 'Upload Photo'.";
        } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
            msg = "No camera found on this device. You can use 'Upload Photo' or enter ingredients manually.";
        }

        if (cameraError && cameraErrorMessage) {
            cameraErrorMessage.innerText = msg;
            cameraError.style.display = "flex";
        }
    }
}

function stopCameraStream() {
    if (state.cameraStream) {
        try {
            state.cameraStream.getTracks().forEach(track => track.stop());
        } catch (e) {
            console.warn("Error stopping camera track:", e);
        }
        state.cameraStream = null;
    }

    const video = document.getElementById("cameraVideo");
    if (video) {
        video.srcObject = null;
    }
}

function switchCamera() {
    state.currentFacingMode = state.currentFacingMode === "environment" ? "user" : "environment";
    startCameraStream();
}

function capturePhoto() {
    const video = document.getElementById("cameraVideo");
    const canvas = document.getElementById("captureCanvas");
    const preview = document.getElementById("capturedImagePreview");
    const frame = document.getElementById("viewfinderFrame");
    const btnCapture = document.getElementById("btnCapturePhoto");
    const btnRetake = document.getElementById("btnRetakePhoto");
    const btnAnalyze = document.getElementById("btnAnalyzeImage");

    if (!video || !canvas || !preview) return;

    const width = video.videoWidth || 640;
    const height = video.videoHeight || 480;

    // Scale down image if necessary (max 1024 on longest edge for fast Groq vision)
    let targetWidth = width;
    let targetHeight = height;
    const maxDim = 1024;

    if (targetWidth > maxDim || targetHeight > maxDim) {
        if (targetWidth > targetHeight) {
            targetHeight = Math.round((targetHeight * maxDim) / targetWidth);
            targetWidth = maxDim;
        } else {
            targetWidth = Math.round((targetWidth * maxDim) / targetHeight);
            targetHeight = maxDim;
        }
    }

    canvas.width = targetWidth;
    canvas.height = targetHeight;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, targetWidth, targetHeight);

    // Compress to JPEG with 0.82 quality
    const dataUri = canvas.toDataURL("image/jpeg", 0.82);
    state.capturedImageDataUri = dataUri;

    // Show captured image preview and hide video
    preview.src = dataUri;
    preview.style.display = "block";
    video.style.display = "none";
    if (frame) frame.style.display = "none";

    // Switch action buttons
    if (btnCapture) btnCapture.style.display = "none";
    if (btnRetake) btnRetake.style.display = "inline-flex";
    if (btnAnalyze) btnAnalyze.style.display = "inline-flex";

    // Automatically trigger vision scan for snappy UX!
    analyzeCapturedImage();
}

function retakePhoto() {
    const video = document.getElementById("cameraVideo");
    const preview = document.getElementById("capturedImagePreview");
    const frame = document.getElementById("viewfinderFrame");
    const btnCapture = document.getElementById("btnCapturePhoto");
    const btnRetake = document.getElementById("btnRetakePhoto");
    const btnAnalyze = document.getElementById("btnAnalyzeImage");
    const detectedSection = document.getElementById("detectedSection");

    state.capturedImageDataUri = null;
    state.detectedIngredients = [];

    if (preview) preview.style.display = "none";
    if (video) video.style.display = "block";
    if (frame) frame.style.display = "block";

    if (btnCapture) btnCapture.style.display = "inline-flex";
    if (btnRetake) btnRetake.style.display = "none";
    if (btnAnalyze) btnAnalyze.style.display = "none";
    if (detectedSection) detectedSection.style.display = "none";
}

function handleFileUpload(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        const rawDataUri = e.target.result;

        // Process through canvas to optimize size
        const img = new Image();
        img.onload = () => {
            const canvas = document.getElementById("captureCanvas");
            const preview = document.getElementById("capturedImagePreview");
            const video = document.getElementById("cameraVideo");
            const frame = document.getElementById("viewfinderFrame");
            const btnCapture = document.getElementById("btnCapturePhoto");
            const btnRetake = document.getElementById("btnRetakePhoto");
            const btnAnalyze = document.getElementById("btnAnalyzeImage");

            let targetWidth = img.width;
            let targetHeight = img.height;
            const maxDim = 1024;

            if (targetWidth > maxDim || targetHeight > maxDim) {
                if (targetWidth > targetHeight) {
                    targetHeight = Math.round((targetHeight * maxDim) / targetWidth);
                    targetWidth = maxDim;
                } else {
                    targetWidth = Math.round((targetWidth * maxDim) / targetHeight);
                    targetHeight = maxDim;
                }
            }

            canvas.width = targetWidth;
            canvas.height = targetHeight;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(img, 0, 0, targetWidth, targetHeight);

            const optimizedDataUri = canvas.toDataURL("image/jpeg", 0.82);
            state.capturedImageDataUri = optimizedDataUri;

            preview.src = optimizedDataUri;
            preview.style.display = "block";
            if (video) video.style.display = "none";
            if (frame) frame.style.display = "none";

            if (btnCapture) btnCapture.style.display = "none";
            if (btnRetake) btnRetake.style.display = "inline-flex";
            if (btnAnalyze) btnAnalyze.style.display = "inline-flex";

            // Trigger AI ingredient analysis
            analyzeCapturedImage();
        };
        img.src = rawDataUri;
    };
    reader.readAsDataURL(file);

    // Reset input value so same file can be re-selected if desired
    event.target.value = "";
}

async function analyzeCapturedImage() {
    if (!state.capturedImageDataUri) {
        showError("Please capture or upload a photo first.");
        return;
    }

    const cameraLoader = document.getElementById("cameraLoader");
    const detectedSection = document.getElementById("detectedSection");
    const detectedChips = document.getElementById("detectedChips");
    const detectedCount = document.getElementById("detectedCount");
    const detectedMessage = document.getElementById("detectedMessage");

    if (cameraLoader) cameraLoader.style.display = "flex";
    if (detectedSection) detectedSection.style.display = "none";

    try {
        const formData = new FormData();

        const parts = state.capturedImageDataUri.split(",");
        const mimeMatch = parts[0].match(/data:(.*?);base64/);

        if (!mimeMatch || !parts[1]) {
            throw new Error("Invalid captured image data.");
        }

        const mimeType = mimeMatch[1];
        const byteString = atob(parts[1]);
        const bytes = new Uint8Array(byteString.length);

        for (let i = 0; i < byteString.length; i++) {
            bytes[i] = byteString.charCodeAt(i);
        }

        const blob = new Blob([bytes], { type: mimeType });
        formData.append("file", blob, "camera-capture.jpg");

        const response = await fetch("/api/camera/analyze", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (cameraLoader) cameraLoader.style.display = "none";

        if (response.status === 429 || data.rate_limited) {
            showError("Groq Vision rate limit reached. Please wait a moment before trying again.");
            return;
        }

        if (!response.ok || data.error) {
            showError(data.error || "Failed to analyze photo.");
            return;
        }

        state.detectedIngredients = data.ingredients || [];

        renderDetectedChips();

        if (detectedCount) {
            detectedCount.innerText = `${state.detectedIngredients.length} found`;
        }

        if (detectedMessage) {
            detectedMessage.innerText = data.message || "";
        }

        if (detectedSection) {
            detectedSection.style.display = "block";
            detectedSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }

    } catch (err) {
        console.error("Image analysis error:", err);
        if (cameraLoader) cameraLoader.style.display = "none";
        showError("Network or server error while scanning photo. Please try again.");
    }
}

function renderDetectedChips() {
    const container = document.getElementById("detectedChips");
    if (!container) return;

    if (state.detectedIngredients.length === 0) {
        container.innerHTML = `<span style="color:var(--text-secondary);font-size:0.9rem;">No clear food ingredients detected. Try snapping with better lighting or adding manually.</span>`;
        return;
    }

    container.innerHTML = state.detectedIngredients.map((item, index) => `
        <span class="detected-chip">
            <span>${typeof item === "object" ? (item.name || "Ingredient") + (item.quantity ? " - " + item.quantity : "") : item}</span>
            <button type="button" class="remove-chip-btn" onclick="removeDetectedIngredient(${index})" title="Remove item">&times;</button>
        </span>
    `).join("");
}

function removeDetectedIngredient(index) {
    state.detectedIngredients.splice(index, 1);
    renderDetectedChips();
    const detectedCount = document.getElementById("detectedCount");
    if (detectedCount) {
        detectedCount.innerText = `${state.detectedIngredients.length} found`;
    }
}

function useDetectedIngredients(mode = "add") {
    if (state.detectedIngredients.length === 0) {
        showError("No detected ingredients to add.");
        return;
    }

    const ingredientsField = document.getElementById("ingredients");
    if (!ingredientsField) return;

    const newItems = state.detectedIngredients
        .map(item => {
            if (typeof item === "object" && item !== null) {
                const name = item.name || "Ingredient";
                const quantity = item.quantity || "";
                return quantity ? `${quantity} ${name}` : name;
            }

            return String(item);
        })
        .filter(Boolean)
        .join(", ");

    if (mode === "replace" || !ingredientsField.value.trim()) {
        ingredientsField.value = newItems;
    } else {
        ingredientsField.value = `${ingredientsField.value.trim()}, ${newItems}`;
    }

    // Close camera modal and focus ingredients field for manual editing
    closeCameraModal();
    ingredientsField.focus();

    // Friendly feedback
    hideError();
}

// ==============================================================================
// RECIPE SUGGESTIONS
// ==============================================================================
async function generateRecipes() {
    hideError();

    const ingredientsInput = document.getElementById("ingredients");
    const ingredients = ingredientsInput ? ingredientsInput.value.trim() : "";
    const cuisine = document.getElementById("cuisine").value;
    const diet = document.getElementById("diet").value;
    const language = document.getElementById("language").value;

    const recipesContainer = document.getElementById("recipesContainer");
    const suggestionsSection = document.getElementById("suggestionsSection");
    const recipeContainer = document.getElementById("recipeContainer");

    if (!ingredients) {
        showError("Please enter, speak, or camera-capture at least one ingredient to generate recipes.");
        if (ingredientsInput) ingredientsInput.focus();
        return;
    }

    // Reset previous views
    if (recipesContainer) recipesContainer.innerHTML = "";
    if (suggestionsSection) suggestionsSection.style.display = "none";
    if (recipeContainer) recipeContainer.style.display = "none";

    showLoader(
        `Crafting 5 ${cuisine !== "Any" ? cuisine : ""} Recipes...`,
        `Selected Diet: ${diet} | Output Language: ${language}`
    );

    try {
        const response = await fetch("/api/ai/suggestions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                ingredients,
                cuisine,
                diet,
                language
            })
        });

        const data = await response.json();
        hideLoader();

        if (response.status === 429 || data.rate_limited) {
            showError("Groq API rate limit reached. Please wait a moment before trying again.");
            return;
        }

        if (!response.ok || data.error) {
            showError(data.error || "Failed to generate recipe suggestions.");
            return;
        }

        const recipes = data.recipes || [];

        if (!Array.isArray(recipes) || recipes.length === 0) {
            showError("No recipes could be generated for these ingredients and preferences. Try adjusting them.");
            return;
        }

        renderSuggestions(recipes);

    } catch (err) {
        console.error("Generate recipes error:", err);
        hideLoader();
        showError("Unable to reach AI service. Please check your connection and try again.");
    }
}

function renderSuggestions(recipes) {
    const recipesContainer = document.getElementById("recipesContainer");
    const suggestionsSection = document.getElementById("suggestionsSection");

    if (!recipesContainer || !suggestionsSection) return;

    recipesContainer.innerHTML = recipes.map(recipe => {
        // Escape single quotes for inline onclick parameter
        const safeName = (recipe.name || "").replace(/'/g, "\\'");
        return `
            <div class="recipe-card" onclick="generateFullRecipe('${safeName}')">
                <div>
                    <h3>${recipe.name || "Untitled Dish"}</h3>
                    <p>${recipe.description || "A delicious recipe idea."}</p>
                </div>
                <div class="card-action">
                    <span>View Full Recipe</span>
                    <span>&rarr;</span>
                </div>
            </div>
        `;
    }).join("");

    suggestionsSection.style.display = "block";
    suggestionsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ==============================================================================
// FULL RECIPE GENERATION & DISPLAY
// ==============================================================================
async function generateFullRecipe(dishName) {
    hideError();

    const cuisine = document.getElementById("cuisine").value;
    const diet = document.getElementById("diet").value;
    const language = document.getElementById("language").value;
    const ingredients = document.getElementById("ingredients").value.trim();
    const recipeContainer = document.getElementById("recipeContainer");

    if (!dishName) {
        showError("Invalid dish name.");
        return;
    }

    state.selectedDishName = dishName;

    showLoader(
        `Cooking up recipe for "${dishName}"...`,
        `Translating & formatting full instructions in ${language}.`
    );

    try {
        const response = await fetch("/api/ai/recipe", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                dish_name: dishName,
                cuisine,
                diet,
                language,
                ingredients
            })
        });

        const data = await response.json();
        hideLoader();

        if (response.status === 429 || data.rate_limited) {
            showError("Groq API rate limit reached. Please wait a moment before trying again.");
            return;
        }

        if (!response.ok || data.error) {
            showError(data.error || "Failed to generate complete recipe details.");
            return;
        }

        const r = { ...data.recipe, id: data.recipe_id };
        if (!r) {
            showError("Incomplete recipe data returned by AI. Please try again.");
            return;
        }

        renderFullRecipe(r);

    } catch (err) {
        console.error("Full recipe error:", err);
        hideLoader();
        showError("Error retrieving full recipe details. Please check connection.");
    }
}

function renderFullRecipe(r) {
    const container = document.getElementById("recipeContainer");
    if (!container) return;

    const nutrition = r.nutrition || {};
    const ingredientsList = Array.isArray(r.ingredients) ? r.ingredients : [];
    const instructionsList = Array.isArray(r.instructions) ? r.instructions : [];
    const similarList = Array.isArray(r.similar) ? r.similar : [];

    const nutritionValue = (value) => {
        return value !== undefined && value !== null && value !== ""
            ? value
            : "-";
    };

    container.innerHTML = `
        <div class="recipe-header">
            <div class="recipe-title-row">
                <h1 class="recipe-title">${r.title || "Culinary Recipe"}</h1>

                <div class="recipe-actions">
                    <button
                        type="button"
                        class="secondary-btn"
                        onclick="saveRecipe(${r.id})"
                        title="Save Recipe"
                    >
                        Save Recipe
                    </button>
                </div>
            </div>

            <p class="recipe-description">
                ${r.description || ""}
            </p>
        </div>

        <!-- Quick Info -->
        <div class="info-grid">
            <div class="info-box">
                <h4>Servings</h4>
                <p>${r.servings || "2"}</p>
            </div>

            <div class="info-box">
                <h4>Prep Time</h4>
                <p>${r.prep_time || "15 mins"}</p>
            </div>

            <div class="info-box">
                <h4>Cook Time</h4>
                <p>${r.cook_time || "25 mins"}</p>
            </div>

            <div class="info-box">
                <h4>Difficulty</h4>
                <p>${r.difficulty || "Easy"}</p>
            </div>
        </div>

        <!-- Nutrition -->
        <div class="nutrition-section">
            <h3 class="section-heading">
                Nutrition Overview (per serving)
            </h3>

            <div class="nutrition-grid">
                <div class="nutrition-card">
                    <h3>${nutritionValue(nutrition.calories)}</h3>
                    <p>Calories</p>
                </div>

                <div class="nutrition-card">
                    <h3>${nutritionValue(nutrition.protein)}</h3>
                    <p>Protein</p>
                </div>

                <div class="nutrition-card">
                    <h3>${nutritionValue(nutrition.carbs)}</h3>
                    <p>Carbohydrates</p>
                </div>

                <div class="nutrition-card">
                    <h3>${nutritionValue(nutrition.fat)}</h3>
                    <p>Fats</p>
                </div>
            </div>
        </div>

        <!-- Recipe Content -->
        <div class="recipe-columns">

            <div class="ingredients-card">
                <h3 class="section-heading">Ingredients</h3>

                <ul class="ingredients-list">
                    ${
                        ingredientsList.length
                            ? ingredientsList.map(item => {
                                const name = item?.name ?? "";
                                const quantity = item?.quantity ?? "";

                                const text = [quantity, name]
                                    .filter(Boolean)
                                    .join(" ");

                                return `
                                    <li>${text || "Ingredient"}</li>
                                `;
                            }).join("")
                            : "<li>No ingredient details available.</li>"
                    }
                </ul>
            </div>

            <div class="instructions-card">
                <h3 class="section-heading">
                    Step-by-Step Instructions
                </h3>

                <ol class="instructions-list">
                    ${
                        instructionsList.length
                            ? instructionsList.map(step => `
                                <li>${step}</li>
                            `).join("")
                            : "<li>No cooking instructions available.</li>"
                    }
                </ol>
            </div>

        </div>

        <!-- Chef Tips -->
        ${
            r.tips
                ? `
                    <div class="chef-tips-card">
                        <div class="tips-icon">Tip</div>
                        <div class="tips-content">
                            <h4>Chef's Secret Tip</h4>
                            <p>${r.tips}</p>
                        </div>
                    </div>
                `
                : ""
        }

        <!-- Similar Dishes -->
        ${
            similarList.length > 0
                ? `
                    <div class="similar-section">
                        <h3 class="section-heading">
                            Similar Dishes You Might Love
                        </h3>

                        <div class="similar-grid">
                            ${
                                similarList.map(item => {
                                    const safeItem = String(item)
                                        .replace(/\\/g, "\\\\")
                                        .replace(/'/g, "\\'");

                                    return `
                                        <button
                                            type="button"
                                            class="similar-chip"
                                            onclick="generateFullRecipe('${safeItem}')"
                                        >
                                            ${item} &rarr;
                                        </button>
                                    `;
                                }).join("")
                            }
                        </div>
                    </div>
                `
                : ""
        }
    `;

    container.style.display = "block";
    container.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}

async function saveRecipe(recipeId) {
    if (!recipeId) {
        showError("Recipe ID is missing.");
        return;
    }

    try {
        const response = await fetch("/api/saved-recipes", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ recipe_id: recipeId })
        });

        const data = await response.json();

        if (response.status === 409) {
            const button = document.querySelector(`button[onclick="saveRecipe(${recipeId})"]`);
            if (button) {
                button.textContent = "Already Saved";
                button.disabled = true;
            }
            return;
        }

        if (!response.ok) {
            showError(data.detail || "Failed to save recipe.");
            return;
        }

        alert("Recipe saved successfully!");
    } catch (err) {
        console.error("Save recipe error:", err);
        showError("Unable to save recipe. Please check the connection.");
    }
}
async function removeSavedRecipe(recipeId) {
    if (!recipeId) {
        showError("Recipe ID is missing.");
        return;
    }

    try {
        const response = await fetch(`/api/saved-recipes/${recipeId}`, {
            method: "DELETE"
        });

        const data = await response.json();

        if (!response.ok) {
            showError(data.detail || "Failed to remove saved recipe.");
            return;
        }

        await loadSavedRecipes();
        alert("Recipe removed from saved recipes.");
    } catch (err) {
        console.error("Remove saved recipe error:", err);
        showError("Unable to remove saved recipe. Please check the connection.");
    }
}
async function loadSavedRecipes() {
    const section = document.getElementById("savedRecipesSection");
    const container = document.getElementById("savedRecipesContainer");

    if (!section || !container) return;

    try {
        const response = await fetch("/api/saved-recipes");
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Failed to load saved recipes.");
        }

        container.innerHTML = "";

        if (!data.length) {
            section.style.display = "none";
            return;
        }

        section.style.display = "block";

        data.forEach(recipe => {
            const card = document.createElement("div");
            card.className = "recipe-card";

            card.innerHTML = `
                <h3>${recipe.title || "Saved Recipe"}</h3>
                <p>${recipe.description || "No description available."}</p>
                <div class="card-action">
                    <span>${recipe.cuisine || "Recipe"}</span>
                    <span>View Recipe</span>
                    <button type="button" class="remove-saved-btn">Remove</button>
                </div>
            `;

            card.addEventListener("click", (event) => {
                if (event.target.closest(".remove-saved-btn")) return;
                loadSavedRecipeDetails(recipe.recipe_id);
            });

            const removeButton = card.querySelector(".remove-saved-btn");
            removeButton.addEventListener("click", async (event) => {
                event.stopPropagation();
                await removeSavedRecipe(recipe.recipe_id);
            });

            container.appendChild(card);
        });
    } catch (err) {
        console.error("Load saved recipes error:", err);
    }
}

async function loadSavedRecipeDetails(recipeId) {
    try {
        const response = await fetch(`/api/recipes/${recipeId}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Failed to load recipe.");
        }

        const r = { ...data, id: recipeId };
        renderFullRecipe(r);

        const container = document.getElementById("recipeContainer");
        if (container) {
            container.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    } catch (err) {
        console.error("Load saved recipe details error:", err);
        showError("Unable to load saved recipe.");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadSavedRecipes();
});













/* ==============================================================================
   AUTHENTICATION
   ============================================================================== */

function showAuthError(message) {
    const box = document.getElementById("authError");
    const text = document.getElementById("authErrorMessage");

    if (text) text.innerText = message || "Authentication failed.";
    if (box) box.style.display = "flex";
}

function hideAuthError() {
    const box = document.getElementById("authError");
    if (box) box.style.display = "none";
}

function openAuthModal(mode = "signin") {
    const modal = document.getElementById("authModal");
    if (!modal) return;

    modal.style.display = "flex";
    hideAuthError();
    switchAuthMode(mode);
}

function closeAuthModal() {
    const modal = document.getElementById("authModal");
    if (modal) modal.style.display = "none";

    hideAuthError();
}

function switchAuthMode(mode) {
    const signinForm = document.getElementById("signinForm");
    const signupForm = document.getElementById("signupForm");
    const title = document.getElementById("authModalTitle");
    const subtitle = document.getElementById("authModalSubtitle");

    hideAuthError();

    if (mode === "signup") {
        if (signinForm) signinForm.style.display = "none";
        if (signupForm) signupForm.style.display = "block";
        if (title) title.innerText = "Create Account";
        if (subtitle) subtitle.innerText = "Create an account to manage your recipes.";
    } else {
        if (signinForm) signinForm.style.display = "block";
        if (signupForm) signupForm.style.display = "none";
        if (title) title.innerText = "Login";
        if (subtitle) subtitle.innerText = "Sign in to save and access your recipes.";
    }
}

function updateAuthUI() {
    const userGreeting = document.getElementById("userGreeting");

    if (!userGreeting) return;

    if (state.isAuthenticated && state.currentUser) {
        const displayName =
            state.currentUser.name ||
            state.currentUser.username ||
            "User";

        userGreeting.innerText = displayName;
    } else {
        userGreeting.innerText = "";
    }
}

async function checkAuthSession() {
    try {
        const response = await fetch("/api/auth/me", {
            method: "GET"
        });

        if (!response.ok) {
            state.currentUser = null;
            state.isAuthenticated = false;
            updateAuthUI();
            return;
        }

        const user = await response.json();

        state.currentUser = user;
        state.isAuthenticated = true;

        updateAuthUI();
        await loadSavedRecipes();
    } catch (err) {
        console.error("Auth session check error:", err);

        state.currentUser = null;
        state.isAuthenticated = false;
        updateAuthUI();
    }
}

async function submitSignin(event) {
    event.preventDefault();
    hideAuthError();

    const identifier = document.getElementById("signinIdentifier")?.value.trim();
    const password = document.getElementById("signinPassword")?.value || "";

    if (!identifier || !password) {
        showAuthError("Username/email and password are required.");
        return;
    }

    try {
        const response = await fetch("/api/auth/signin", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                identifier,
                password
            })
        });

        const data = await response.json();

        if (!response.ok) {
            showAuthError(data.detail || "Invalid username/email or password.");
            return;
        }

        state.currentUser = data;
        state.isAuthenticated = true;

        updateAuthUI();
        closeAuthModal();

        await loadSavedRecipes();
    } catch (err) {
        console.error("Signin error:", err);
        showAuthError("Unable to reach the server. Please try again.");
    }
}

async function submitSignup(event) {
    event.preventDefault();
    hideAuthError();

    const name = document.getElementById("signupName")?.value.trim();
    const username = document.getElementById("signupUsername")?.value.trim();
    const email = document.getElementById("signupEmail")?.value.trim();
    const password = document.getElementById("signupPassword")?.value || "";
    const confirmPassword = document.getElementById("signupConfirmPassword")?.value || "";

    if (!name || !username || !email || !password || !confirmPassword) {
        showAuthError("Please fill in all required fields.");
        return;
    }

    if (password !== confirmPassword) {
        showAuthError("Passwords do not match.");
        return;
    }

    try {
        const response = await fetch("/api/auth/signup", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name,
                username,
                email,
                password,
                confirm_password: confirmPassword
            })
        });

        const data = await response.json();

        if (!response.ok) {
            showAuthError(data.detail || "Unable to create account.");
            return;
        }

        document.getElementById("signinIdentifier").value = username;
        document.getElementById("signinPassword").value = "";

        switchAuthMode("signin");

        const signinMessage = document.getElementById("authModalSubtitle");
        if (signinMessage) {
            signinMessage.innerText = "Account created successfully. Please log in.";
        }
    } catch (err) {
        console.error("Signup error:", err);
        showAuthError("Unable to reach the server. Please try again.");
    }
}

async function logoutUser() {
    try {
        const response = await fetch("/api/auth/logout", {
            method: "POST"
        });

        if (!response.ok && response.status !== 204) {
            throw new Error("Logout failed.");
        }

        state.currentUser = null;
        state.isAuthenticated = false;

        updateAuthUI();

        const section = document.getElementById("savedRecipesSection");
        const container = document.getElementById("savedRecipesContainer");

        if (container) container.innerHTML = "";
        if (section) section.style.display = "none";

        window.location.href = "/login";
    } catch (err) {
        console.error("Logout error:", err);
        showError("Unable to log out. Please try again.");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    checkAuthSession();
});







