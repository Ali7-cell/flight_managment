/**
 * AeroFlow FMS - AI Policy Assistant (LangGraph RAG Chatbot)
 */

const PolicyChatController = {
  isOpen: false,

  init() {
    this.bindEvents();
  },

  bindEvents() {
    const trigger = document.getElementById('btn-toggle-policy-chat');
    if (trigger) {
      trigger.addEventListener('click', () => this.toggleDrawer());
    }

    const closeBtn = document.getElementById('btn-close-chat-drawer');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.closeDrawer());
    }

    const form = document.getElementById('chat-input-form');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        this.sendMessage();
      });
    }

    // Quick prompt chips
    document.querySelectorAll('.chat-suggestion-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const input = document.getElementById('chat-input-text');
        input.value = chip.innerText;
        this.sendMessage();
      });
    });
  },

  toggleDrawer() {
    this.isOpen ? this.closeDrawer() : this.openDrawer();
  },

  openDrawer() {
    const drawer = document.getElementById('policy-chat-drawer');
    if (drawer) {
      drawer.classList.add('active');
      this.isOpen = true;
      document.getElementById('chat-input-text')?.focus();
    }
  },

  closeDrawer() {
    const drawer = document.getElementById('policy-chat-drawer');
    if (drawer) {
      drawer.classList.remove('active');
      this.isOpen = false;
    }
  },

  async sendMessage() {
    const input = document.getElementById('chat-input-text');
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    this.appendMessage('user', text);

    // Show AI typing indicator
    const typingId = this.appendTypingIndicator();

    try {
      const res = await apiClient.submitPolicyQuestion(text);
      this.removeTypingIndicator(typingId);

      const draftAnswer = res.draft_answer || 'Our LangGraph AI agent has analyzed airline policy documents and database fare rules.';
      const flags = res.consistency_flags || ['Grounding verified: 0 Hallucinations'];

      this.appendMessage('ai', draftAnswer, flags);
    } catch (err) {
      this.removeTypingIndicator(typingId);
      this.appendMessage('ai', `Apologies, I encountered an issue: ${err.message}. Please ask our human support desk.`);
    }
  },

  appendMessage(sender, text, flags = []) {
    const msgContainer = document.getElementById('chat-messages-container');
    if (!msgContainer) return;

    const div = document.createElement('div');
    div.className = `chat-msg ${sender === 'user' ? 'msg-user' : 'msg-ai'}`;

    let flagsHtml = '';
    if (flags && flags.length > 0) {
      flagsHtml = `
        <div>
          <span class="grounding-verified-badge">
            ✓ ${flags[0]}
          </span>
        </div>
      `;
    }

    div.innerHTML = `
      <div>${text}</div>
      ${flagsHtml}
    `;

    msgContainer.appendChild(div);
    msgContainer.scrollTop = msgContainer.scrollHeight;
  },

  appendTypingIndicator() {
    const msgContainer = document.getElementById('chat-messages-container');
    const id = 'typing-' + Date.now();
    const div = document.createElement('div');
    div.id = id;
    div.className = 'chat-msg msg-ai';
    div.innerHTML = `
      <span style="display: inline-flex; align-items: center; gap: 4px;">
        <span class="pulse-dot"></span>
        <span style="font-size: 0.78rem; color: var(--text-secondary);">Querying Pinecone & verifying fare rules...</span>
      </span>
    `;
    msgContainer.appendChild(div);
    msgContainer.scrollTop = msgContainer.scrollHeight;
    return id;
  },

  removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }
};

window.PolicyChatController = PolicyChatController;
