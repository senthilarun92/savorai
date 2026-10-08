const signinForm = document.getElementById("signinForm");
const signupForm = document.getElementById("signupForm");
const authTitle = document.getElementById("authTitle");
const authSubtitle = document.getElementById("authSubtitle");
const authSwitchText = document.getElementById("authSwitchText");
const authSwitchBtn = document.getElementById("authSwitchBtn");
const authNotice = document.getElementById("authNotice");
const googleBtn = document.getElementById("googleBtn");

function showNotice(message, type = "error") {
    if (!authNotice) return;

    authNotice.textContent = message;
    authNotice.hidden = false;
    authNotice.classList.toggle("success", type === "success");
}

function hideNotice() {
    if (!authNotice) return;
    authNotice.hidden = true;
    authNotice.textContent = "";
    authNotice.classList.remove("success");
}

function switchAuthMode(mode) {
    hideNotice();

    const signup = mode === "signup";

    if (signinForm) signinForm.hidden = signup;
    if (signupForm) signupForm.hidden = !signup;

    if (authTitle) {
        authTitle.textContent = signup
            ? "Join SavorAI"
            : "Good to See You";
    }

    if (authSubtitle) {
        authSubtitle.textContent = signup
            ? "Create smarter meals and discover recipes with AI."
            : "Sign in to discover your next favorite meal.";
    }

    if (authSwitchText) {
        authSwitchText.textContent = signup
            ? "Already have an account?"
            : "New here?";
    }

    if (authSwitchBtn) {
        authSwitchBtn.textContent = signup
            ? "Login"
            : "Create an account";
    }
}

authSwitchBtn?.addEventListener("click", () => {
    const showingSignup = signupForm && !signupForm.hidden;
    switchAuthMode(showingSignup ? "signin" : "signup");
});

async function signIn(identifier, password) {
    const response = await fetch("/api/auth/signin", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ identifier, password })
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || "Unable to sign in.");
    }

    return data;
}

signinForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideNotice();

    const identifier = document.getElementById("signinIdentifier")?.value.trim();
    const password = document.getElementById("signinPassword")?.value || "";

    if (!identifier || !password) {
        showNotice("Please enter your username/email and password.");
        return;
    }

    const button = signinForm.querySelector("button[type='submit']");

    try {
        if (button) {
            button.disabled = true;
            button.textContent = "Signing in...";
        }

        await signIn(identifier, password);
        window.location.href = "/app";
    } catch (error) {
        showNotice(error.message);
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = "Login";
        }
    }
});

signupForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideNotice();

    const name = document.getElementById("signupName")?.value.trim() || "";
    const username = document.getElementById("signupUsername")?.value.trim() || "";
    const email = document.getElementById("signupEmail")?.value.trim() || "";
    const password = document.getElementById("signupPassword")?.value || "";
    const confirmPassword = document.getElementById("signupConfirmPassword")?.value || "";

    if (password !== confirmPassword) {
        showNotice("Passwords do not match.");
        return;
    }

    const button = signupForm.querySelector("button[type='submit']");

    try {
        if (button) {
            button.disabled = true;
            button.textContent = "Creating account...";
        }

        const response = await fetch("/api/auth/signup", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name: name || null,
                username,
                email,
                password,
                confirm_password: confirmPassword
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Unable to create account.");
        }

        await signIn(username, password);
        window.location.href = "/app";
    } catch (error) {
        showNotice(error.message);
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = "Create Account";
        }
    }
});

googleBtn?.addEventListener("click", () => {
    window.location.href = "/api/auth/google/start";
});

const googleError = new URLSearchParams(
    window.location.search
).get("google_error");

if (googleError === "1") {
    showNotice(
        "Google sign-in could not be completed. Please try again.",
        "error"
    );
}

switchAuthMode("signin");

