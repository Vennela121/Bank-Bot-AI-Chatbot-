// ---------------------- MODAL CONTROLS ----------------------
const loginModal = document.getElementById("loginModal");
const registerModal = document.getElementById("registerModal");
const loginBtn = document.getElementById("loginBtn");
const registerBtn = document.getElementById("registerBtn");
const logoutBtn = document.getElementById("logoutBtn");
const closeBtns = document.querySelectorAll(".close");

// Open/Close modals
loginBtn?.addEventListener("click", () => loginModal.style.display = "block");
registerBtn?.addEventListener("click", () => registerModal.style.display = "block");

closeBtns.forEach(btn => btn.addEventListener("click", () => {
    loginModal.style.display = "none";
    registerModal.style.display = "none";
}));

window.addEventListener("click", e => {
    if (e.target === loginModal) loginModal.style.display = "none";
    if (e.target === registerModal) registerModal.style.display = "none";
});

// ---------------------- CHATBOT CONTROLS ----------------------
const toggleBtn = document.getElementById("toggle-btn");
const chatbotBody = document.querySelector(".chatbot-body");
const fullscreenBtn = document.getElementById("fullscreen-btn");
const chatbot = document.getElementById("chatbot");

toggleBtn?.addEventListener("click", () => {
    chatbotBody.classList.toggle("hide");
    toggleBtn.textContent = chatbotBody.classList.contains("hide") ? "+" : "_";
});

fullscreenBtn?.addEventListener("click", () => {
    chatbot.classList.toggle("fullscreen");
});

// Chat messages
const sendBtn = document.getElementById("send-btn");
const userInput = document.getElementById("user-input");
const chatMessages = document.querySelector(".chat-messages");

function addMessage(sender, text) {
    const msg = document.createElement("p");
    msg.innerHTML = `<strong>${sender}:</strong> ${text.replace(/\n/g, "<br>")}`;
    if (chatMessages) {
        chatMessages.appendChild(msg);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

sendBtn?.addEventListener("click", async () => {
    const message = userInput.value.trim();
    if (!message) return;
    addMessage("You", message);
    userInput.value = "";
    await handleChatMessage(message);
});

userInput?.addEventListener("keypress", e => {
    if (e.key === "Enter") {
        e.preventDefault();
        sendBtn.click();
    }
});
//Chatbot logic
async function handleChatMessage(message) {
    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: message })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        const botReply = data.response;
        const intent = data.intent;

        addMessage("Bot", `${botReply}<br><span style="color:green;">✔ ${intent}</span>`);

    } catch (err) {
        console.error("Chatbot error:", err);
        addMessage("Bot", "⚠️ Server error. Please try again later.");
    }
}
// ---------------------- LOGIN FORM ----------------------
// ---------------------- LOGIN FORM (UPDATED) ----------------------
const loginForm = document.getElementById("loginForm");
loginForm?.addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = new FormData(loginForm);
    const email = formData.get("email");
    const password = formData.get("password");

    try {
        const response = await fetch("/api/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email: email, password: password })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Store user data in localStorage only after successful backend login
            localStorage.setItem("user", JSON.stringify(data.user)); 
            alert("✅ Login successful!");
            window.location.href = "profile.html";
        } else {
            alert(`❌ Login failed: ${data.message || 'Invalid credentials'}`);
        }

    } catch (err) {
        console.error("Login error:", err);
        alert("⚠️ An error occurred. Please try again.");
    }
});
// ---------------------- REGISTER FORM ----------------------
// ---------------------- REGISTER FORM (CORRECTED) ----------------------
const registerForm = document.getElementById("registerForm");
registerForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(registerForm);
    const data = Object.fromEntries(formData.entries());
    
    // Use the correct key for account number from your HTML
    data.account_number = data.account; 
    delete data.account; 
    
    try {
        const response = await fetch("/api/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        alert(result.message);
        
        if (result.success) {
            registerModal.style.display = "none";
        }

    } catch (error) {
        console.error("Registration error:", error);
        alert("An error occurred during registration. Please try again.");
    }
});
// ---------------------- PROFILE PAGE ----------------------
// ---------------------- PROFILE PAGE (CORRECTED) ----------------------
function loadProfileFromLocalStorage() {
    const user = JSON.parse(localStorage.getItem("user"));
    if (!user) {
        alert("Please log in first!");
        window.location.href = "index.html";
        return;
    }

    document.getElementById("userName").textContent = user.name || "User";
    document.getElementById("userEmail").textContent = user.email || "N/A";
    // This is the line that needs to be fixed.
    document.getElementById("userAccount").textContent = user.account_number || "---"; 
    document.getElementById("userEmail").textContent = user.email;
    // And this line too.
    document.getElementById("userBalance").textContent = parseFloat(user.balance).toFixed(2) || "0";
}

// ---------------------- LOGOUT ----------------------
function logout() {
    localStorage.removeItem("user");
    alert("✅ Logged out successfully!");
    updateLoginUI();
    if (window.location.pathname.endsWith('profile.html')) {
        window.location.href = "index.html";
    }
}

// ---------------------- UPDATE LOGIN/LOGOUT BUTTONS ----------------------
function updateLoginUI() {
    const user = JSON.parse(localStorage.getItem("user"));
    if (user) {
        loginBtn?.style.setProperty('display', 'none');
        registerBtn?.style.setProperty('display', 'none');
        logoutBtn?.style.setProperty('display', 'inline-block');
    } else {
        loginBtn?.style.setProperty('display', 'inline-block');
        registerBtn?.style.setProperty('display', 'inline-block');
        logoutBtn?.style.setProperty('display', 'none');
    }
}

// ---------------------- DUMMY ACCOUNT HISTORY ----------------------
const historyBtn = document.getElementById("historyBtn");
const historySection = document.getElementById("historySection");

const dummyTransactions = [
    { date: "2025-09-20 10:00 AM", type: "Deposit", amount: 5000, details: "Initial Deposit" },
    { date: "2025-09-21 02:30 PM", type: "Withdrawal", amount: 1000, details: "ATM Withdrawal" },
    { date: "2025-09-21 05:00 PM", type: "Transfer", amount: 2000, details: "Sent to Friend" },
    { date: "2025-09-22 11:00 AM", type: "Deposit", amount: 3000, details: "Salary Credited" },
    { date: "2025-09-23 03:15 PM", type: "Payment", amount: 500, details: "Shopping Payment" }
];

function loadDummyHistory() {
    let html = "<table><tr><th>Date</th><th>Type</th><th>Amount</th><th>Details</th></tr>";
    dummyTransactions.forEach(tx => {
        html += `<tr>
                    <td>${tx.date}</td>
                    <td>${tx.type}</td>
                    <td>₹${tx.amount.toFixed(2)}</td>
                    <td>${tx.details}</td>
                 </tr>`;
    });
    html += "</table>";
    historySection.innerHTML = html;
}

historyBtn?.addEventListener("click", () => {
    if (historySection.style.display === "none" || historySection.style.display === "") {
        historySection.style.display = "block";
        loadDummyHistory();
    } else {
        historySection.style.display = "none";
    }
});

// ---------------------- INITIALIZE ----------------------
document.addEventListener("DOMContentLoaded", () => {
    updateLoginUI();
    if (window.location.pathname.endsWith('profile.html')) {
        loadProfileFromLocalStorage();
    }
    logoutBtn?.addEventListener("click", logout);
});
