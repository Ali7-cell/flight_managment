/**
 * AeroFlow FMS - Core Application State & Orchestration
 */

const App = {
  currentTab: 'tab-search',

  init() {
    this.bindGlobalEvents();
    this.checkBackendHealth();
    this.updateAuthUI();

    // Initialize sub-controllers
    if (window.BookingController) BookingController.init();
    if (window.WaitlistController) WaitlistController.init();
    if (window.PolicyChatController) PolicyChatController.init();
    if (window.AdminController) AdminController.init();
  },

  bindGlobalEvents() {
    // Navigation tabs
    document.querySelectorAll('.nav-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const targetTab = btn.dataset.target;
        if (targetTab) this.switchTab(targetTab);
      });
    });

    // Modal close buttons
    document.querySelectorAll('.modal-close-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const modal = btn.closest('.modal-overlay');
        if (modal) modal.classList.remove('active');
      });
    });

    // Close modal on click outside dialog
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          overlay.classList.remove('active');
        }
      });
    });

    // Auth trigger button
    const authBtn = document.getElementById('btn-auth-trigger');
    if (authBtn) {
      authBtn.addEventListener('click', () => this.handleAuthButtonClick());
    }

    // Auth form submit
    const authForm = document.getElementById('auth-modal-form');
    if (authForm) {
      authForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.submitAuth();
      });
    }

    // Auth mode toggle (Login <-> Signup)
    const toggleAuthMode = document.getElementById('toggle-auth-mode-btn');
    if (toggleAuthMode) {
      toggleAuthMode.addEventListener('click', () => this.toggleAuthMode());
    }
  },

  switchTab(tabId) {
    this.currentTab = tabId;

    // Update nav buttons
    document.querySelectorAll('.nav-tab-btn').forEach(btn => {
      if (btn.dataset.target === tabId) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Update view panels
    document.querySelectorAll('.tab-view').forEach(view => {
      if (view.id === tabId) {
        view.classList.add('active');
      } else {
        view.classList.remove('active');
      }
    });

    window.scrollTo({ top: 0, behavior: 'smooth' });
  },

  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('active');
  },

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('active');
  },

  showToast(message, type = 'info', title = null) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = {
      success: '✓',
      error: '✕',
      warning: '⚠',
      info: 'ℹ',
    };

    const titles = {
      success: title || 'Success',
      error: title || 'Error Occurred',
      warning: title || 'Attention',
      info: title || 'System Update',
    };

    toast.innerHTML = `
      <div class="toast-icon">${icons[type] || 'ℹ'}</div>
      <div class="toast-content">
        <div class="toast-title">${titles[type]}</div>
        <div class="toast-message">${message}</div>
      </div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(50px)';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  },

  async checkBackendHealth() {
    const isHealthy = await apiClient.checkHealth();
    const indicator = document.getElementById('health-indicator-pill');
    if (indicator) {
      if (isHealthy) {
        indicator.innerHTML = `<span class="pulse-dot"></span> API Online (Port 8000)`;
        indicator.style.color = 'var(--accent-emerald)';
      } else {
        indicator.innerHTML = `<span class="pulse-dot" style="background-color: var(--accent-amber); box-shadow: 0 0 8px var(--accent-amber);"></span> Mock Mode Active`;
        indicator.style.color = 'var(--accent-amber)';
      }
    }
  },

  // Auth Handling
  isSignupMode: false,

  handleAuthButtonClick() {
    const token = apiClient.getAuthToken();
    if (token) {
      if (confirm('Do you want to log out?')) {
        apiClient.setAuthToken(null, null);
        this.updateAuthUI();
        this.showToast('You have been logged out.', 'info');
      }
    } else {
      this.openModal('auth-modal');
    }
  },

  toggleAuthMode() {
    this.isSignupMode = !this.isSignupMode;
    const titleEl = document.getElementById('auth-modal-title');
    const submitBtn = document.getElementById('auth-submit-btn');
    const toggleBtn = document.getElementById('toggle-auth-mode-btn');
    const nameGroup = document.getElementById('auth-fullname-group');

    if (this.isSignupMode) {
      titleEl.innerText = 'Create AeroFlow Account';
      submitBtn.innerText = 'Sign Up';
      toggleBtn.innerText = 'Already have an account? Log In';
      nameGroup.style.display = 'flex';
    } else {
      titleEl.innerText = 'Log In to AeroFlow';
      submitBtn.innerText = 'Log In';
      toggleBtn.innerText = "Don't have an account? Sign Up";
      nameGroup.style.display = 'none';
    }
  },

  async submitAuth() {
    const email = document.getElementById('auth-email').value.trim();
    const password = document.getElementById('auth-password').value;
    const fullName = document.getElementById('auth-fullname').value.trim();

    try {
      let res;
      if (this.isSignupMode) {
        res = await apiClient.signup(email, fullName, password);
        this.showToast('Account created successfully!', 'success');
      } else {
        res = await apiClient.login(email, password);
        this.showToast('Welcome back!', 'success');
      }

      apiClient.setAuthToken(res.access_token, {
        email,
        full_name: fullName || email.split('@')[0],
        role: res.role || 'customer'
      });

      this.closeModal('auth-modal');
      this.updateAuthUI();
    } catch (err) {
      this.showToast(`Authentication failed: ${err.message}`, 'error');
    }
  },

  async quickLogin(email, password) {
    try {
      const res = await apiClient.login(email, password);
      apiClient.setAuthToken(res.access_token, {
        email,
        full_name: email.split('@')[0],
        role: res.role || 'customer'
      });
      this.closeModal('auth-modal');
      this.updateAuthUI();
      this.showToast(`Logged in as ${(res.role || 'customer').toUpperCase()}`, 'success');
      if (res.role === 'super_admin' || res.role === 'ops_agent') {
        this.switchTab('tab-admin');
      }
    } catch (err) {
      this.showToast(`Quick login failed: ${err.message}`, 'error');
    }
  },

  updateAuthUI() {
    const btn = document.getElementById('btn-auth-trigger');
    const user = apiClient.getCurrentUser();
    const token = apiClient.getAuthToken();

    if (token && user.email) {
      btn.innerHTML = `👤 ${user.full_name || user.email} (${user.role || 'customer'})`;
      btn.style.borderColor = 'var(--accent-cyan)';
    } else {
      btn.innerHTML = `👤 Log In / Sign Up`;
      btn.style.borderColor = 'var(--border-glass)';
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  App.init();
});

window.App = App;
