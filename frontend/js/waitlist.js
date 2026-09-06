/**
 * AeroFlow FMS - Priority Waitlist Controller
 */

const WaitlistController = {
  currentFlightId: null,
  currentSeatClassId: null,

  init() {
    this.bindEvents();
  },

  bindEvents() {
    const form = document.getElementById('waitlist-form');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        this.submitWaitlist();
      });
    }

    const checkForm = document.getElementById('check-waitlist-form');
    if (checkForm) {
      checkForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.checkPosition();
      });
    }
  },

  openWaitlistModal(flightId, seatClassId, flightNumber, className) {
    this.currentFlightId = flightId;
    this.currentSeatClassId = seatClassId;

    document.getElementById('waitlist-flight-title').innerText = `${flightNumber} • ${className.toUpperCase()}`;
    const user = apiClient.getCurrentUser();
    if (user.email) {
      document.getElementById('waitlist-passenger-email').value = user.email;
    }
    if (user.full_name) {
      document.getElementById('waitlist-passenger-name').value = user.full_name;
    }

    App.openModal('waitlist-modal');
  },

  async submitWaitlist() {
    const email = document.getElementById('waitlist-passenger-email').value.trim();
    const name = document.getElementById('waitlist-passenger-name').value.trim();
    const quantity = parseInt(document.getElementById('waitlist-quantity').value, 10) || 1;

    if (!email || !name) {
      App.showToast('Please enter your name and email address.', 'warning');
      return;
    }

    try {
      App.showToast('Adding to high-concurrency waitlist queue...', 'info');
      const res = await apiClient.joinWaitlist(this.currentFlightId, this.currentSeatClassId, quantity, email, name);
      App.closeModal('waitlist-modal');
      App.showToast(`Joined Waitlist! Position: #${res.position || 1}`, 'success');

      // Store in local storage for quick tracking
      localStorage.setItem('aeroflow_last_waitlist', JSON.stringify({
        flightId: this.currentFlightId,
        entryId: res.waitlist_entry_id,
        position: res.position || 1,
        email: email
      }));

      App.switchTab('tab-waitlist');
      this.renderPositionCard(res.position || 1, 'Waiting for seat release');
    } catch (err) {
      App.showToast(`Waitlist error: ${err.message}`, 'error');
    }
  },

  async checkPosition() {
    const flightId = document.getElementById('waitlist-check-flight-id').value.trim();
    const entryId = document.getElementById('waitlist-check-entry-id').value.trim();

    if (!flightId) {
      App.showToast('Please provide a Flight ID.', 'warning');
      return;
    }

    try {
      App.showToast('Querying real-time queue position...', 'info');
      const res = await apiClient.getWaitlistPosition(flightId, entryId || null);
      this.renderPositionCard(res.position, res.status);
    } catch (err) {
      App.showToast(`Lookup failed: ${err.message}`, 'error');
    }
  },

  renderPositionCard(position, status) {
    const container = document.getElementById('waitlist-result-display');
    if (!container) return;

    container.innerHTML = `
      <div class="search-card" style="margin-top: 1.5rem; text-align: center;">
        <span class="brand-badge" style="margin-bottom: 0.5rem; display: inline-block;">LIVE QUEUE STATUS</span>
        <div style="font-size: 3.5rem; font-weight: 900; color: var(--accent-cyan); line-height: 1.2;">
          #${position}
        </div>
        <p style="color: var(--text-primary); font-weight: 600; font-size: 1.1rem; margin-bottom: 0.5rem;">
          You are number ${position} in line!
        </p>
        <p style="color: var(--text-secondary); font-size: 0.85rem; max-width: 480px; margin: 0 auto 1.5rem;">
          Our background automated LangGraph worker will automatically promote your reservation and notify you via email the second a seat is canceled or released.
        </p>
        <div class="system-status-indicator" style="display: inline-flex;">
          <span class="pulse-dot"></span>
          Status: ${status || 'Active Waiting'}
        </div>
      </div>
    `;
  }
};

window.WaitlistController = WaitlistController;
