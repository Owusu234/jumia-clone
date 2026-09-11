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
      <button id="sv-chat-mic" type="button" title="Speak instead of typing" aria-label="Speak your message">🎤</button>
      <button id="sv-chat-send">Send</button>
    </div>
  `;

  document.body.appendChild(bubble);
  document.body.appendChild(panel);

  const messagesEl = panel.querySelector("#sv-chat-messages");
  const inputEl = panel.querySelector("#sv-chat-input");
  const sendBtn = panel.querySelector("#sv-chat-send");
  const closeBtn = panel.querySelector("#sv-chat-close");
  const micBtn = panel.querySelector("#sv-chat-mic");

  let history = [];
  let greeted = false;

  // ---- Draggable bubble ----
  // Lets the user reposition the launcher anywhere on screen; the spot is
  // remembered (per browser) so it stays put on the next visit.
  const POSITION_KEY = "sv_chat_bubble_pos";
  const DRAG_THRESHOLD = 6; // px before a press counts as a drag instead of a click
  const EDGE_GAP = 8;

  let dragPointerId = null;
  let dragMoved = false;
  let dragStartX = 0, dragStartY = 0, bubbleStartLeft = 0, bubbleStartTop = 0;

  function clamp(val, min, max) {
    return Math.max(min, Math.min(max, val));
  }

  function placeBubble(left, top) {
    const w = bubble.offsetWidth || 60;
    const h = bubble.offsetHeight || 60;
    left = clamp(left, EDGE_GAP, Math.max(EDGE_GAP, window.innerWidth - w - EDGE_GAP));
    top = clamp(top, EDGE_GAP, Math.max(EDGE_GAP, window.innerHeight - h - EDGE_GAP));
    bubble.style.left = left + "px";
    bubble.style.top = top + "px";
    bubble.style.right = "auto";
    bubble.style.bottom = "auto";
    return { left, top };
  }

  function positionPanelNearBubble() {
    const bRect = bubble.getBoundingClientRect();
    const panelWidth = Math.min(340, window.innerWidth * 0.92);
    const panelHeight = Math.min(460, window.innerHeight * 0.75);
    const gap = 14;

    let top = bRect.top - gap - panelHeight;
    if (top < EDGE_GAP) top = Math.min(bRect.bottom + gap, window.innerHeight - panelHeight - EDGE_GAP);
    top = clamp(top, EDGE_GAP, Math.max(EDGE_GAP, window.innerHeight - panelHeight - EDGE_GAP));

    let left = bRect.right - panelWidth;
    left = clamp(left, EDGE_GAP, Math.max(EDGE_GAP, window.innerWidth - panelWidth - EDGE_GAP));

    panel.style.left = left + "px";
    panel.style.top = top + "px";
    panel.style.right = "auto";
    panel.style.bottom = "auto";
  }

  function savePosition(left, top) {
    try {
      localStorage.setItem(POSITION_KEY, JSON.stringify({ left, top }));
    } catch (err) {
      /* localStorage unavailable (private mode etc.) — position just won't persist */
    }
  }

  function restorePosition() {
    try {
      const saved = JSON.parse(localStorage.getItem(POSITION_KEY) || "null");
      if (saved && typeof saved.left === "number" && typeof saved.top === "number") {
        placeBubble(saved.left, saved.top);
      }
    } catch (err) {
      /* ignore malformed/unavailable storage */
    }
  }

  bubble.addEventListener("pointerdown", (e) => {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    dragPointerId = e.pointerId;
    dragMoved = false;
    const rect = bubble.getBoundingClientRect();
    bubbleStartLeft = rect.left;
    bubbleStartTop = rect.top;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    e.preventDefault();
  });

  // Listen on window (not the bubble itself) for move/up: this way the drag
  // keeps tracking even once the pointer moves faster than the bubble and
  // ends up outside its 60x60 box — no dependency on setPointerCapture,
  // which isn't reliably supported everywhere.
  window.addEventListener("pointermove", (e) => {
    if (dragPointerId === null || dragPointerId !== e.pointerId) return;
    const dx = e.clientX - dragStartX;
    const dy = e.clientY - dragStartY;
    if (!dragMoved && (Math.abs(dx) > DRAG_THRESHOLD || Math.abs(dy) > DRAG_THRESHOLD)) {
      dragMoved = true;
      bubble.classList.add("sv-dragging");
    }
    if (dragMoved) {
      placeBubble(bubbleStartLeft + dx, bubbleStartTop + dy);
      if (panel.classList.contains("open")) positionPanelNearBubble();
    }
  });

  function endDrag(e) {
    if (dragPointerId === null || dragPointerId !== e.pointerId) return;
    dragPointerId = null;
    bubble.classList.remove("sv-dragging");
    if (dragMoved) {
      const rect = bubble.getBoundingClientRect();
      savePosition(rect.left, rect.top);
    }
  }
  window.addEventListener("pointerup", endDrag);
  window.addEventListener("pointercancel", endDrag);

  window.addEventListener("resize", () => {
    const rect = bubble.getBoundingClientRect();
    if (bubble.style.left) placeBubble(rect.left, rect.top);
    if (panel.classList.contains("open")) positionPanelNearBubble();
  });

  restorePosition();

  bubble.addEventListener("click", (e) => {
    // A drag that just ended fires a click right after pointerup — swallow it
    // so dragging the bubble doesn't also toggle the chat panel open/closed.
    if (dragMoved) {
      dragMoved = false;
      e.preventDefault();
      e.stopPropagation();
      return;
    }
    panel.classList.toggle("open");
    if (panel.classList.contains("open")) positionPanelNearBubble();
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
