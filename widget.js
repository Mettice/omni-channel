/**
 * Omni AI Embeddable Widget
 *
 * Usage:
 * <script src="https://your-domain.com/widget.js"
 *   data-api="https://your-api.com"
 *   data-position="right"
 *   data-color="#6366f1"
 *   data-title="Support"
 * ></script>
 */

(function() {
  'use strict';

  // Get configuration from script tag
  const currentScript = document.currentScript;
  const config = {
    api: currentScript?.getAttribute('data-api') || 'https://omni-channel-production-54be.up.railway.app',
    position: currentScript?.getAttribute('data-position') || 'right',
    color: currentScript?.getAttribute('data-color') || '#6366f1',
    title: currentScript?.getAttribute('data-title') || 'Omni AI',
    greeting: currentScript?.getAttribute('data-greeting') || 'Hi! How can I help you today?'
  };

  // Generate session ID
  let sessionId = localStorage.getItem('omni_widget_session');
  if (!sessionId) {
    sessionId = 'widget_' + Math.random().toString(36).substring(2, 10);
    localStorage.setItem('omni_widget_session', sessionId);
  }

  // CSS Styles
  const styles = `
    #omni-widget-container * {
      box-sizing: border-box;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    #omni-widget-btn {
      position: fixed;
      bottom: 24px;
      ${config.position}: 24px;
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: ${config.color};
      border: none;
      cursor: pointer;
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.3s ease;
      z-index: 999998;
    }

    #omni-widget-btn:hover {
      transform: scale(1.1);
      box-shadow: 0 6px 32px rgba(0, 0, 0, 0.3);
    }

    #omni-widget-btn svg {
      width: 28px;
      height: 28px;
      fill: white;
    }

    #omni-widget-btn.open svg.chat-icon { display: none; }
    #omni-widget-btn.open svg.close-icon { display: block; }
    #omni-widget-btn:not(.open) svg.chat-icon { display: block; }
    #omni-widget-btn:not(.open) svg.close-icon { display: none; }

    #omni-widget-frame {
      position: fixed;
      bottom: 100px;
      ${config.position}: 24px;
      width: 380px;
      height: 550px;
      border-radius: 16px;
      background: #1e293b;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
      overflow: hidden;
      opacity: 0;
      transform: translateY(20px) scale(0.95);
      transition: all 0.3s ease;
      pointer-events: none;
      z-index: 999997;
      display: flex;
      flex-direction: column;
    }

    #omni-widget-frame.open {
      opacity: 1;
      transform: translateY(0) scale(1);
      pointer-events: auto;
    }

    .omni-widget-header {
      padding: 16px 20px;
      background: linear-gradient(135deg, #1e293b 0%, rgba(99, 102, 241, 0.1) 100%);
      border-bottom: 1px solid #334155;
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .omni-widget-avatar {
      width: 40px;
      height: 40px;
      background: linear-gradient(135deg, ${config.color} 0%, #0ea5e9 100%);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .omni-widget-avatar svg {
      width: 20px;
      height: 20px;
      stroke: white;
      fill: none;
    }

    .omni-widget-title {
      flex: 1;
    }

    .omni-widget-title h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: #f8fafc;
    }

    .omni-widget-title span {
      font-size: 12px;
      color: #10b981;
    }

    .omni-widget-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .omni-widget-message {
      max-width: 85%;
      padding: 12px 16px;
      border-radius: 16px;
      font-size: 14px;
      line-height: 1.5;
      animation: omniMsgIn 0.3s ease;
    }

    @keyframes omniMsgIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .omni-widget-message.agent {
      background: #334155;
      color: #f8fafc;
      align-self: flex-start;
      border-bottom-left-radius: 4px;
    }

    .omni-widget-message.user {
      background: ${config.color};
      color: white;
      align-self: flex-end;
      border-bottom-right-radius: 4px;
    }

    .omni-widget-typing {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
      background: #334155;
      border-radius: 16px;
      border-bottom-left-radius: 4px;
      align-self: flex-start;
    }

    .omni-widget-typing-dots {
      display: flex;
      gap: 4px;
    }

    .omni-widget-typing-dots span {
      width: 6px;
      height: 6px;
      background: #94a3b8;
      border-radius: 50%;
      animation: omniBounce 1.4s infinite ease-in-out;
    }

    .omni-widget-typing-dots span:nth-child(1) { animation-delay: 0s; }
    .omni-widget-typing-dots span:nth-child(2) { animation-delay: 0.2s; }
    .omni-widget-typing-dots span:nth-child(3) { animation-delay: 0.4s; }

    @keyframes omniBounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-4px); }
    }

    .omni-widget-input {
      padding: 16px;
      background: #1e293b;
      border-top: 1px solid #334155;
      display: flex;
      gap: 12px;
    }

    .omni-widget-input input {
      flex: 1;
      padding: 12px 16px;
      border-radius: 10px;
      border: 1px solid #334155;
      background: #334155;
      color: #f8fafc;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
    }

    .omni-widget-input input::placeholder {
      color: #64748b;
    }

    .omni-widget-input input:focus {
      border-color: ${config.color};
    }

    .omni-widget-input button {
      width: 44px;
      height: 44px;
      border-radius: 10px;
      border: none;
      background: ${config.color};
      color: white;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s;
    }

    .omni-widget-input button:hover {
      filter: brightness(1.1);
    }

    .omni-widget-input button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .omni-widget-input button svg {
      width: 18px;
      height: 18px;
      stroke: white;
      fill: none;
    }

    .omni-widget-powered {
      padding: 8px;
      text-align: center;
      font-size: 10px;
      color: #64748b;
      background: #0f172a;
    }

    .omni-widget-powered a {
      color: #818cf8;
      text-decoration: none;
    }

    @media (max-width: 480px) {
      #omni-widget-frame {
        width: calc(100% - 32px);
        height: calc(100% - 140px);
        bottom: 100px;
        left: 16px;
        right: 16px;
      }
    }
  `;

  // HTML Template
  const template = `
    <button id="omni-widget-btn" aria-label="Open chat">
      <svg class="chat-icon" viewBox="0 0 24 24">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      </svg>
      <svg class="close-icon" viewBox="0 0 24 24">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
    </button>
    <div id="omni-widget-frame">
      <div class="omni-widget-header">
        <div class="omni-widget-avatar">
          <svg viewBox="0 0 24 24" stroke-width="2">
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" x2="12" y1="19" y2="22"/>
          </svg>
        </div>
        <div class="omni-widget-title">
          <h3>${config.title}</h3>
          <span>● Online</span>
        </div>
      </div>
      <div class="omni-widget-messages" id="omni-messages">
        <div class="omni-widget-message agent">${config.greeting}</div>
      </div>
      <div class="omni-widget-input">
        <input type="text" id="omni-input" placeholder="Type a message..." autocomplete="off">
        <button id="omni-send" aria-label="Send">
          <svg viewBox="0 0 24 24" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>
      <div class="omni-widget-powered">
        Powered by <a href="#" target="_blank">Omni AI</a>
      </div>
    </div>
  `;

  // Create container
  const container = document.createElement('div');
  container.id = 'omni-widget-container';
  container.innerHTML = template;

  // Add styles
  const styleSheet = document.createElement('style');
  styleSheet.textContent = styles;
  document.head.appendChild(styleSheet);

  // Add to DOM when ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => document.body.appendChild(container));
  } else {
    document.body.appendChild(container);
  }

  // Wait for DOM
  function init() {
    const btn = document.getElementById('omni-widget-btn');
    const frame = document.getElementById('omni-widget-frame');
    const messages = document.getElementById('omni-messages');
    const input = document.getElementById('omni-input');
    const sendBtn = document.getElementById('omni-send');

    let isOpen = false;

    // Toggle widget
    btn.addEventListener('click', () => {
      isOpen = !isOpen;
      btn.classList.toggle('open', isOpen);
      frame.classList.toggle('open', isOpen);
      if (isOpen) input.focus();
    });

    // Escape HTML
    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    // Add message
    function addMessage(text, type) {
      const div = document.createElement('div');
      div.className = `omni-widget-message ${type}`;
      div.textContent = text;
      messages.appendChild(div);
      messages.scrollTop = messages.scrollHeight;
    }

    // Add typing indicator
    function showTyping() {
      const div = document.createElement('div');
      div.className = 'omni-widget-typing';
      div.id = 'omni-typing';
      div.innerHTML = '<div class="omni-widget-typing-dots"><span></span><span></span><span></span></div>';
      messages.appendChild(div);
      messages.scrollTop = messages.scrollHeight;
    }

    function hideTyping() {
      const typing = document.getElementById('omni-typing');
      if (typing) typing.remove();
    }

    // Send message
    async function sendMessage() {
      const text = input.value.trim();
      if (!text) return;

      addMessage(text, 'user');
      input.value = '';
      sendBtn.disabled = true;
      showTyping();

      try {
        const res = await fetch(`${config.api}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ player_id: sessionId, message: text })
        });

        const data = await res.json();
        hideTyping();
        addMessage(data.response || 'Sorry, something went wrong.', 'agent');
      } catch (error) {
        console.error('Omni Widget Error:', error);
        hideTyping();
        addMessage('Connection error. Please try again.', 'agent');
      }

      sendBtn.disabled = false;
    }

    // Event listeners
    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') sendMessage();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    setTimeout(init, 0);
  }
})();
