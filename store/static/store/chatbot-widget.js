/* ShopVibe AI Recommendation Chatbot — shared chat panel.
   Desktop launcher: sidebar Chat item.
   Mobile launcher: bottom navigation Chat item.
   No floating action button exists or is created anywhere. */

(function () {
  const ENDPOINT = "/api/chatbot/recommend/";
  const mobileChatBtn = document.getElementById("sv-mobile-chat-button");
  const desktopChatBtn = document.getElementById("sv-desktop-chat-button");

  // Remove any legacy floating launcher left in the DOM by an older cached
  // chatbot script. The navigation buttons are the only supported launchers.
  const removeLegacyFloatingElements = () => {
    removeLegacyFloatingElements();
  };
  removeLegacyFloatingElements();

  const panel = document.createElement("div");
  panel.id = "sv-chat-panel";
  panel.innerHTML = `
    <div id="sv-chat-header">
      <div>
        Shopping Assistant
        <span class="sub">Tell me what you're looking for</span>
      </div>
      <div id="sv-chat-close" role="button" tabindex="0" aria-label="Close chat">&times;</div>
    </div>
    <div id="sv-chat-messages"></div>
    <div id="sv-chat-input-row">
      <input id="sv-chat-input" type="text" placeholder="e.g. something formal for a wedding" />
      <button id="sv-chat-mic" type="button" title="Speak instead of typing" aria-label="Speak your message">🎤</button>
      <button id="sv-chat-send">Send</button>
    </div>
  `;
  document.body.appendChild(panel);

  const messagesEl = panel.querySelector("#sv-chat-messages");
  const inputEl = panel.querySelector("#sv-chat-input");
  const sendBtn = panel.querySelector("#sv-chat-send");
  const closeBtn = panel.querySelector("#sv-chat-close");
  const micBtn = panel.querySelector("#sv-chat-mic");
  let history = [];
  let greeted = false;

  function positionDesktopPanel() {
    if (!desktopChatBtn || window.innerWidth <= 767) return;
    const r = desktopChatBtn.getBoundingClientRect();
    const width = Math.min(360, window.innerWidth * 0.92);
    const height = Math.min(500, window.innerHeight * 0.78);
    let left = r.right + 14;
    if (left + width > window.innerWidth - 12) left = r.left;
    let top = r.top;
    top = Math.max(12, Math.min(top, window.innerHeight - height - 12));
    panel.style.left = `${left}px`;
    panel.style.top = `${top}px`;
    panel.style.right = "auto";
    panel.style.bottom = "auto";
  }

  function positionMobilePanel() {
    if (window.innerWidth > 767) return;
    panel.style.left = "8px";
    panel.style.right = "8px";
    panel.style.top = "auto";
    panel.style.bottom = "calc(74px + env(safe-area-inset-bottom))";
  }

  function toggleChat() {
    const willOpen = !panel.classList.contains("open");
    panel.classList.toggle("open", willOpen);
    mobileChatBtn?.classList.toggle("active", willOpen);
    desktopChatBtn?.classList.toggle("active", willOpen);
    if (!willOpen) return;
    if (window.innerWidth <= 767) positionMobilePanel();
    else positionDesktopPanel();
    if (!greeted) {
      addBotMessage("Hi! Tell me what you're shopping for and I'll suggest a few things from the store.");
      greeted = true;
    }
    setTimeout(() => inputEl.focus(), 0);
  }

  // Navigation buttons are wired directly to the assistant.
  // No navigation/default action is allowed to run for these launchers.
  mobileChatBtn?.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    toggleChat();
  });
  desktopChatBtn?.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    toggleChat();
  });
  closeBtn.addEventListener("click", () => {
    panel.classList.remove("open");
    mobileChatBtn?.classList.remove("active");
    desktopChatBtn?.classList.remove("active");
  });
  closeBtn.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") closeBtn.click();
  });
  window.ShopVibeChat = {
    toggle: toggleChat,
    close: () => {
      panel.classList.remove("open");
      mobileChatBtn?.classList.remove("active");
      desktopChatBtn?.classList.remove("active");
    }
  };

  // Defensive cleanup against an older cached script creating the legacy bubble.
  const bubbleGuard = new MutationObserver(() => {
    removeLegacyFloatingElements();
  });
  bubbleGuard.observe(document.body, { childList: true });

  window.addEventListener("resize", () => {
    if (!panel.classList.contains("open")) return;
    if (window.innerWidth <= 767) positionMobilePanel();
    else positionDesktopPanel();
  });

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

  // ---- Voice input (Web Speech API) ----
  // Lets the user speak their message instead of typing it.
  const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;

  // The Web Speech API also requires a secure context (HTTPS, or
  // localhost/127.0.0.1 in dev). On plain HTTP the constructor still
  // exists, so the old check alone let the mic render and then fail
  // silently the moment it was clicked. Check both up front.
  const speechAvailable = !!SpeechRecognitionAPI && window.isSecureContext;

  if (!speechAvailable) {
    // Hide the mic rather than showing a button that silently fails,
    // and say why so it's clear this isn't a bug.
    micBtn.style.display = "none";
    if (SpeechRecognitionAPI && !window.isSecureContext) {
      console.warn("ShopVibe chatbot: voice input needs HTTPS (or localhost) — mic hidden.");
    }
  } else {
    const recognition = new SpeechRecognitionAPI();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = true;

    let isListening = false;
    let finalTranscript = "";

    recognition.onstart = () => {
      isListening = true;
      finalTranscript = "";
      micBtn.classList.add("listening");
      micBtn.innerText = "⏹";
      micBtn.title = "Stop listening";
      inputEl.placeholder = "Listening...";
    };

    recognition.onresult = (event) => {
      let interimTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }
      inputEl.value = (finalTranscript + interimTranscript).trim();
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        addBotMessage("I couldn't access your microphone. Please check your browser's microphone permissions.");
      }
    };

    const resetMicUI = () => {
      isListening = false;
      micBtn.classList.remove("listening");
      micBtn.innerText = "🎤";
      micBtn.title = "Speak instead of typing";
      inputEl.placeholder = "e.g. something formal for a wedding";
    };

    recognition.onend = () => {
      resetMicUI();
      // Auto-send the transcribed message, just like pressing Enter after typing.
      if (inputEl.value.trim()) {
        sendMessage();
      }
    };

    micBtn.addEventListener("click", () => {
      if (isListening) {
        recognition.stop();
      } else {
        inputEl.value = "";
        try {
          recognition.start();
        } catch (err) {
          console.error("Could not start speech recognition:", err);
        }
      }
    });
  }
})();
