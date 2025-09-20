// --- Modal controls for Login & Register ---
const loginModal = document.getElementById("loginModal");
const registerModal = document.getElementById("registerModal");
const loginBtn = document.getElementById("loginBtn");
const registerBtn = document.getElementById("registerBtn");
const closeBtns = document.querySelectorAll(".close");

loginBtn.onclick = () => loginModal.style.display = "block";
registerBtn.onclick = () => registerModal.style.display = "block";
closeBtns.forEach(btn => btn.onclick = () => {
  loginModal.style.display = "none";
  registerModal.style.display = "none";
});
window.onclick = (e) => {
  if (e.target === loginModal) loginModal.style.display = "none";
  if (e.target === registerModal) registerModal.style.display = "none";
};

// --- Chatbot controls ---
const toggleBtn = document.getElementById("toggle-btn");
const chatbotBody = document.querySelector(".chatbot-body");
const fullscreenBtn = document.getElementById("fullscreen-btn");
const chatbot = document.getElementById("chatbot");

toggleBtn.addEventListener("click", () => {
  chatbotBody.classList.toggle("hide");
  toggleBtn.textContent = chatbotBody.classList.contains("hide") ? "+" : "_";
});
fullscreenBtn.addEventListener("click", () => {
  chatbot.classList.toggle("fullscreen");
});

// --- Chat functionality ---
const sendBtn = document.getElementById("send-btn");
const userInput = document.getElementById("user-input");
const chatMessages = document.querySelector(".chat-messages");

// 🔴 Removed saveMessage() since we don't want localStorage anymore

function addMessage(sender, text) {
  const msg = document.createElement("p");
  msg.innerHTML = `<strong>${sender}:</strong> ${text.replace(/\n/g, "<br>")}`;
  chatMessages.appendChild(msg);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 🔴 Removed "Load chat history" block so nothing restores on reload

sendBtn.addEventListener("click", async () => {
  const message = userInput.value.trim();
  if (!message) return;
  addMessage("You", message);
  userInput.value = "";
  await callChatAPI(message);
});

userInput.addEventListener("keypress", (e) => {
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

// --- Login form handler ---
const loginForm = loginModal.querySelector("form");
if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = loginForm.querySelector('input[type="text"]').value;
    const password = loginForm.querySelector('input[type="password"]').value;

    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
        credentials: "include"
      });
      const data = await res.json();
      if (data.success) {
        alert("✅ Login successful!");
        loginModal.style.display = "none";
        addMessage("Bot", "✅ You are now logged in! Try checking your balance.");
      } else {
        alert("❌ " + (data.message || "Login failed."));
      }
    } catch (err) {
      console.error("Login error:", err);
      alert("⚠ Error logging in.");
    }
  });
}

// --- Register form handler ---
const registerForm = registerModal.querySelector("form");
if (registerForm) {
  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const inputs = registerForm.querySelectorAll('input');
    const name = inputs[0].value;
    const email = inputs[1].value;
    const account_number = inputs[2].value;
    const password = inputs[3].value;

    try {
      const res = await fetch("/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, account_number, password }),
        credentials: "include"
      });

      const data = await res.json();
      if (data.success) {
        alert("✅ Registration successful! Please login.");
        registerModal.style.display = "none";
      } else {
        alert("❌ " + (data.message || "Registration failed."));
      }
    } catch (err) {
      console.error("Register error:", err);
      alert("⚠️ Error registering.");
    }
  });
}
