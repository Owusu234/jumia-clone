/* ShopVibe AI Recommendation Chatbot — widget logic
   Include after chatbot-widget.css and this <script> on any page
   (e.g. base.html) where you want the chat bubble to appear. */

(function () {
  const ENDPOINT = "/api/chatbot/recommend/"; // matches chatbot_urls_snippet.py

  // ---- Build DOM ----
  const bubble = document.createElement("div");
  bubble.id = "sv-chat-bubble";
  bubble.innerText = "💬";

  const panel = document.createElement("div");
  panel.id = "sv-chat-panel";
  panel.innerHTML = `
    <div id="sv-chat-header">
      <div>
        Shopping Assistant
        <span class="sub">Tell me what you're looking for</span>
      </div>
      <div id="sv-chat-close">&times;</div>
    </div>
    <div id="sv-chat-messages"></div>
    <div id="sv-chat-input-row">
      <input id="sv-chat-input" type="text" placeholder="e.g. something formal for a wedding" />
      <button id="sv-chat-send">Send</button>
    </div>
  `;

  document.body.appendChild(bubble);
  document.body.appendChild(panel);

  const messagesEl = panel.querySelector("#sv-chat-messages");
  const inputEl = panel.querySelector("#sv-chat-input");
  const sendBtn = panel.querySelector("#sv-chat-send");
  const closeBtn = panel.querySelector("#sv-chat-close");

  let history = [];
  let greeted = false;

  bubble.addEventListener("click", () => {
    panel.classList.toggle("open");
    if (!greeted) {
      addBotMessage("Hi! Tell me what you're shopping for and I'll suggest a few things from the store.");
      greeted = true;
    }
  });
  closeBtn.addEventListener("click", () => panel.classList.remove("open"));

  function addUserMessage(text) {
    const el = document.createElement("div");
    el.className = "sv-msg user";
    el.innerText = text;
    messagesEl.appendChild(el);
    scrollToBottom();
  }

  function addBotMessage(text) {
    const el = document.createElement("div");
    el.className = "sv-msg bot";
    el.innerText = text;
    messagesEl.appendChild(el);
    scrollToBottom();
    return el;
  }

  function addProductCards(products) {
    if (!products || products.length === 0) return;
    const wrap = document.createElement("div");
    wrap.className = "sv-product-cards";
    products.forEach((p) => {
      const a = document.createElement("a");
      a.className = "sv-product-card";
      a.href = p.slug ? `/product/${p.slug}/` : "#"; // adjust to your URL scheme
      a.innerHTML = `
        <img src="${p.image_url || ""}" alt="${escapeHtml(p.name || "")}" />
        <div class="info">
          <div class="name">${escapeHtml(p.name || "")}</div>
          <div class="price">${p.price != null ? "$" + p.price : ""}</div>
        </div>
      `;
      wrap.appendChild(a);
    });
    messagesEl.appendChild(wrap);
    scrollToBottom();
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.innerText = str;
    return div.innerHTML;
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function getCookie(name) {
    // Needed if you keep CSRF protection on the view instead of @csrf_exempt
    const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return match ? match[2] : null;
  }

  async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text) return;
    inputEl.value = "";
    sendBtn.disabled = true;

    addUserMessage(text);
    const loadingEl = addBotMessage("Thinking...");
    loadingEl.classList.add("loading");

    history.push({ role: "user", content: text });

    try {
      const res = await fetch(ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"), // required — your project has CSRF protection on
        },
        body: JSON.stringify({ message: text, history }),
      });
      const data = await res.json();

      loadingEl.remove();

      if (data.error) {
        addBotMessage("Sorry, something went wrong. Please try again.");
        console.error(data.error);
      } else {
        addBotMessage(data.reply || "Here's what I found:");
        addProductCards(data.products);
        history.push({ role: "assistant", content: data.reply || "" });
      }
    } catch (err) {
      loadingEl.remove();
      addBotMessage("Sorry, I couldn't reach the assistant right now.");
      console.error(err);
    } finally {
      sendBtn.disabled = false;
      inputEl.focus();
    }
  }

  sendBtn.addEventListener("click", sendMessage);
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
  });
})();
