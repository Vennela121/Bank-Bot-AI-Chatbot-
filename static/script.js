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
    await callChatAPI(message);
});

userInput?.addEventListener("keypress", e => {
    if (e.key === "Enter") {
        e.preventDefault();
        sendBtn.click();
    }
});

async function callChatAPI(message) {
    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message }),
            credentials: "include"
        });
        const data = await res.json();
        const botReply = data.response || "Sorry, I didn’t understand that.";
        const intent = data.intent || "unknown";
        addMessage("Bot", `${botReply}<br><span style="color:green;"> ✔ ${intent} </span>`);
    } catch (err) {
        console.error("Chat API error:", err);
        addMessage("Bot", "⚠️ Server error. Is the backend running?");
    }
}

// ---------------------- LOGIN FORM ----------------------
const loginForm = document.getElementById("loginForm");
loginForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    const formData = new FormData(loginForm);
    const email = formData.get("email");
    const password = formData.get("password");

    const users = JSON.parse(localStorage.getItem("registeredUsers")) || [];
    const user = users.find(u => u.email === email && u.password === password);

    if (!user) {
        alert("❌ Invalid email or password!");
        return;
    }

    localStorage.setItem("user", JSON.stringify(user));
    alert("✅ Login successful!");
    window.location.href = "profile.html";
});

// ---------------------- REGISTER FORM ----------------------
const registerForm = document.getElementById("registerForm");
registerForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    const formData = new FormData(registerForm);
    const name = formData.get("name");
    const email = formData.get("email");
    const account = formData.get("account");
    const password = formData.get("password");

    const users = JSON.parse(localStorage.getItem("registeredUsers")) || [];
    if (users.some(u => u.email === email)) {
        alert("❌ Email already registered!");
        return;
    }

    const newUser = { name, email, account, password, balance: 50000 };
    users.push(newUser);
    localStorage.setItem("registeredUsers", JSON.stringify(users));

    alert("✅ Registration successful! Please login.");
    registerModal.style.display = "none";
});

// ---------------------- PROFILE PAGE ----------------------
function loadProfileFromLocalStorage() {
    const user = JSON.parse(localStorage.getItem("user"));
    if (!user) {
        alert("Please log in first!");
        window.location.href = "index.html";
        return;
    }

    document.getElementById("userName").textContent = user.name || "User";
    document.getElementById("userEmail").textContent = user.email || "N/A";
    document.getElementById("userAccount").textContent = user.account || "---";
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

// ---------------------- INITIALIZE ----------------------
document.addEventListener("DOMContentLoaded", () => {
    updateLoginUI();
    if (window.location.pathname.endsWith('profile.html')) {
        loadProfileFromLocalStorage();
    }
    logoutBtn?.addEventListener("click", logout);
});
// ---------------------- DUMMY ACCOUNT HISTORY ----------------------
const historyBtn = document.getElementById("historyBtn");
const historySection = document.getElementById("historySection");

// Sample transactions
const dummyTransactions = [
    { date: "2025-09-20 10:00 AM", type: "Deposit", amount: 5000, details: "Initial Deposit" },
    { date: "2025-09-21 02:30 PM", type: "Withdrawal", amount: 1000, details: "ATM Withdrawal" },
    { date: "2025-09-21 05:00 PM", type: "Transfer", amount: 2000, details: "Sent to Friend" },
    { date: "2025-09-22 11:00 AM", type: "Deposit", amount: 3000, details: "Salary Credited" },
    { date: "2025-09-23 03:15 PM", type: "Payment", amount: 500, details: "Shopping Payment" }
];

// Show dummy transactions
function loadDummyHistory() {
    let html = "<table border='1' cellpadding='5'><tr><th>Date</th><th>Type</th><th>Amount</th><th>Details</th></tr>";
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

// Toggle history display
historyBtn?.addEventListener("click", () => {
    if (historySection.style.display === "none") {
        historySection.style.display = "block";
        loadDummyHistory();
    } else {
        historySection.style.display = "none";
    }
});

