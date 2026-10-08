// Full unit & integration simulation tests for Voice Input Feature
const assert = require("assert");

// Load the relevant functions and logic directly from static/app.js
const fs = require("fs");
const path = require("path");

const appJsCode = fs.readFileSync(path.join(__dirname, "../static/app.js"), "utf8");

// Mock browser DOM and environment
const mockDOM = {
    elements: {
        ingredients: { value: "", focus: () => {} },
        language: { value: "English" },
        btnVoice: {
            classList: {
                classes: new Set(),
                add(c) { this.classes.add(c); },
                remove(c) { this.classes.delete(c); },
                contains(c) { return this.classes.has(c); }
            }
        },
        voiceBanner: { style: { display: "none" } },
        voiceIcon: { innerText: "🎤" },
        voiceText: { innerText: "Voice Input" },
        errorBox: { style: { display: "none" }, scrollIntoView: () => {} },
        errorMessage: { innerText: "" }
    }
};

global.document = {
    addEventListener: () => {},
    getElementById(id) {
        return mockDOM.elements[id] || null;
    }
};

global.localStorage = {
    getItem: () => null,
    setItem: () => {}
};

// Mock SpeechRecognition API
class MockSpeechRecognition {
    constructor() {
        this.continuous = false;
        this.interimResults = false;
        this.maxAlternatives = 1;
        this.lang = "en-US";
        this.onstart = null;
        this.onresult = null;
        this.onerror = null;
        this.onend = null;
        this.isStarted = false;
        MockSpeechRecognition.instances.push(this);
    }

    start() {
        if (this.isStarted) {
            throw new Error("InvalidStateError: Failed to execute 'start' on 'SpeechRecognition': recognition has already started.");
        }
        this.isStarted = true;
        MockSpeechRecognition.activeCount++;
        if (this.onstart) this.onstart();
    }

    stop() {
        if (this.isStarted) {
            this.isStarted = false;
            MockSpeechRecognition.activeCount--;
            if (this.onend) this.onend();
        }
    }

    abort() {
        this.stop();
    }

    // Helper to simulate receiving speech results
    simulateResult(transcript, isFinal = true, resultIndex = 0) {
        if (!this.onresult) return;
        const event = {
            resultIndex: resultIndex,
            results: [
                {
                    0: { transcript: transcript },
                    isFinal: isFinal
                }
            ]
        };
        this.onresult(event);
    }
}
MockSpeechRecognition.instances = [];
MockSpeechRecognition.activeCount = 0;

global.window = {
    SpeechRecognition: MockSpeechRecognition
};

const vm = require("vm");
// Make top-level const/let bind to global so assertions can access them
const wrappedCode = appJsCode
    .replace(/^const state\s*=/m, "global.state =")
    .replace(/^const compoundPrefixes\s*=/m, "global.compoundPrefixes =")
    .replace(/^const compoundSuffixes\s*=/m, "global.compoundSuffixes =");

vm.runInThisContext(wrappedCode);

// Helper to reset DOM state between tests
function resetTestState() {
    mockDOM.elements.ingredients.value = "";
    mockDOM.elements.language.value = "English";
    stopVoiceInput();
    MockSpeechRecognition.instances = [];
    MockSpeechRecognition.activeCount = 0;
}

console.log("=== RUNNING VOICE FEATURE QA SUITE ===");

// -------------------------------------------------------------
// TEST 1: Click Voice Input, Say "onion" once -> "onion" only once
// -------------------------------------------------------------
resetTestState();
startVoiceInput();
assert.strictEqual(state.isVoiceListening, true, "Voice should be listening");
assert.strictEqual(mockDOM.elements.voiceText.innerText, "Listening...", "UI should show Listening");
assert.strictEqual(state.speechRecognition.continuous, true, "Continuous must be true");
assert.strictEqual(state.speechRecognition.interimResults, false, "Interim must be false");

// Simulate saying "onion"
state.speechRecognition.simulateResult("onion", true, 0);
assert.strictEqual(mockDOM.elements.ingredients.value, "onion", "TEST 1 Failed: expected 'onion'");
stopVoiceInput();
assert.strictEqual(mockDOM.elements.ingredients.value, "onion", "TEST 1 Failed: value changed after stop");
console.log("✓ TEST 1 Passed: 'onion' spoken once -> 'onion' only once");

// -------------------------------------------------------------
// TEST 2: Say "onion tomato" -> "onion, tomato"
// -------------------------------------------------------------
resetTestState();
startVoiceInput();
state.speechRecognition.simulateResult("onion tomato", true, 0);
assert.strictEqual(mockDOM.elements.ingredients.value, "onion, tomato", "TEST 2 Failed: expected 'onion, tomato'");
stopVoiceInput();
console.log("✓ TEST 2 Passed: 'onion tomato' -> 'onion, tomato'");

// -------------------------------------------------------------
// TEST 3: Say "onion tomato potato garlic coriander"
// -------------------------------------------------------------
resetTestState();
startVoiceInput();
state.speechRecognition.simulateResult("onion tomato potato garlic coriander", true, 0);
assert.strictEqual(
    mockDOM.elements.ingredients.value,
    "onion, tomato, potato, garlic, coriander",
    "TEST 3 Failed: expected all ingredients without duplicates"
);
stopVoiceInput();
console.log("✓ TEST 3 Passed: long phrase captured cleanly without duplicate tokens");

// -------------------------------------------------------------
// TEST 4: Existing textarea: "fish, red onion", say "tomato" -> "fish, red onion, tomato"
// -------------------------------------------------------------
resetTestState();
mockDOM.elements.ingredients.value = "fish, red onion";
startVoiceInput();
state.speechRecognition.simulateResult("tomato", true, 0);
assert.strictEqual(
    mockDOM.elements.ingredients.value,
    "fish, red onion, tomato",
    "TEST 4 Failed: expected 'fish, red onion, tomato'"
);
stopVoiceInput();
console.log("✓ TEST 4 Passed: existing ingredients preserved and not overwritten");

// -------------------------------------------------------------
// TEST 5: Say "onion" twice intentionally -> no accidental duplicate
// -------------------------------------------------------------
resetTestState();
startVoiceInput();
state.speechRecognition.simulateResult("onion", true, 0);
assert.strictEqual(mockDOM.elements.ingredients.value, "onion");

// Second utterance in same session
state.speechRecognition.simulateResult("onion", true, 0);
assert.strictEqual(mockDOM.elements.ingredients.value, "onion", "TEST 5 Failed: duplicate 'onion' was added");
stopVoiceInput();
console.log("✓ TEST 5 Passed: saying 'onion' twice does not duplicate");

// -------------------------------------------------------------
// TEST 6: Start voice -> speak -> stop manually -> no auto-restart
// -------------------------------------------------------------
resetTestState();
startVoiceInput();
assert.strictEqual(state.isVoiceListening, true);
stopVoiceInput();
assert.strictEqual(state.isVoiceListening, false);
assert.strictEqual(state.voiceUserRequestedStop, true);
assert.strictEqual(MockSpeechRecognition.activeCount, 0, "No active recognition instance should remain");
console.log("✓ TEST 6 Passed: manual stop permanently stops recognition without auto-restart");

// -------------------------------------------------------------
// TEST 7: Guard against starting already-running instance (InvalidStateError)
// -------------------------------------------------------------
resetTestState();
startVoiceInput();
const initialInstance = state.speechRecognition;
// Attempt duplicate start call
startVoiceInput();
assert.strictEqual(state.speechRecognition, initialInstance, "Should not create duplicate instance while active");
assert.strictEqual(MockSpeechRecognition.activeCount, 1, "Only 1 active instance allowed");
stopVoiceInput();
console.log("✓ TEST 7 Passed: duplicate start guarded against InvalidStateError");

// -------------------------------------------------------------
// TEST 8: Language selection affects SpeechRecognition locale
// -------------------------------------------------------------
resetTestState();
mockDOM.elements.language.value = "Tamil";
startVoiceInput();
assert.strictEqual(state.speechRecognition.lang, "ta-IN", "Speech recognition lang should be ta-IN for Tamil");
stopVoiceInput();

mockDOM.elements.language.value = "French";
startVoiceInput();
assert.strictEqual(state.speechRecognition.lang, "fr-FR", "Speech recognition lang should be fr-FR for French");
stopVoiceInput();
console.log("✓ TEST 8 Passed: language selection properly sets speech recognition locale");

// -------------------------------------------------------------
// TEST 9: Friendly error handling (not crashing on errors)
// -------------------------------------------------------------
resetTestState();
startVoiceInput();
// Simulate no-speech error: should NOT terminate or show error box
state.speechRecognition.onerror({ error: "no-speech" });
assert.strictEqual(state.isVoiceListening, true, "no-speech should not terminate continuous session");
assert.strictEqual(mockDOM.elements.errorBox.style.display, "none", "no-speech should not show error banner");

// Simulate not-allowed error
state.speechRecognition.onerror({ error: "not-allowed" });
assert.strictEqual(state.isVoiceListening, false, "Fatal error should stop listening");
assert.strictEqual(mockDOM.elements.errorBox.style.display, "flex", "Fatal error should display message");
console.log("✓ TEST 9 Passed: errors handled gracefully without raw JavaScript alerts or crashes");

console.log("\n=========================================");
console.log("ALL 9 QA TESTS PASSED WITH 100% SUCCESS!");
console.log("=========================================\n");

