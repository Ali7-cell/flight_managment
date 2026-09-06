/**
 * AeroFlow FMS - Admin & Operations Tower Controller
 */

const AdminController = {
  init() {
    this.bindEvents();
  },

  bindEvents() {
    const createForm = document.getElementById('admin-create-flight-form');
    if (createForm) {
      createForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.createFlight();
      });
    }

    const resizeForm = document.getElementById('admin-resize-seat-form');
    if (resizeForm) {
      resizeForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.resizeSeatClass();
      });
    }

    const auditForm = document.getElementById('admin-audit-form');
    if (auditForm) {
      auditForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.fetchAuditLogs();
      });
    }

    const refreshPendingBtn = document.getElementById('btn-refresh-pending-policy');
    if (refreshPendingBtn) {
      refreshPendingBtn.addEventListener('click', () => this.loadPendingPolicyRuns());
    }

    const refreshCompBtn = document.getElementById('btn-refresh-compensations');
    if (refreshCompBtn) {
      refreshCompBtn.addEventListener('click', () => this.loadPendingCompensations());
    }
  },

  async createFlight() {
    const flightNumber = document.getElementById('admin-flight-number').value.trim();
    const origin = document.getElementById('admin-origin').value.trim().toUpperCase();
    const destination = document.getElementById('admin-destination').value.trim().toUpperCase();
    const departure = document.getElementById('admin-dep-time').value;
    const arrival = document.getElementById('admin-arr-time').value;
    const ecoSeats = parseInt(document.getElementById('admin-eco-seats').value, 10) || 120;
    const bizSeats = parseInt(document.getElementById('admin-biz-seats').value, 10) || 24;
    const fstSeats = parseInt(document.getElementById('admin-fst-seats').value, 10) || 8;

    const payload = {
      flight_number: flightNumber,
      origin,
      destination,
      origin_tz: 'America/New_York',
      destination_tz: 'Europe/London',
      departure_local: departure,
      arrival_local: arrival,
      seat_allocation: {
        economy: ecoSeats,
        business: bizSeats,
        first: fstSeats
      }
    };

    try {
      App.showToast('Registering flight schedule with DB triggers...', 'info');
      const res = await apiClient.adminCreateFlight(payload);
      App.showToast(`Flight ${flightNumber} created successfully!`, 'success');
      document.getElementById('admin-create-flight-form').reset();
    } catch (err) {
      App.showToast(`Creation failed: ${err.message}`, 'error');
    }
  },

  async resizeSeatClass() {
    const flightId = document.getElementById('admin-resize-flight-id').value.trim();
    const className = document.getElementById('admin-resize-class-name').value;
    const newTotal = document.getElementById('admin-resize-new-total').value;

    try {
      App.showToast('Updating seat capacity under DB invariant lock...', 'info');
      await apiClient.adminResizeSeatClass(flightId, className, newTotal);
      App.showToast(`Seat class ${className} updated to ${newTotal} seats.`, 'success');
    } catch (err) {
      App.showToast(`Resize failed (trigger protected): ${err.message}`, 'error');
    }
  },

  async fetchAuditLogs() {
    const flightId = document.getElementById('admin-audit-flight-id').value.trim();
    if (!flightId) {
      App.showToast('Please enter a Flight ID.', 'warning');
      return;
    }

    const tableBody = document.getElementById('admin-audit-table-body');
    tableBody.innerHTML = `<tr><td colspan="4" style="text-align:center;">Loading audit trail...</td></tr>`;

    try {
      const logs = await apiClient.adminGetAuditLog(flightId);
      if (!logs || logs.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">No audit entries recorded for this flight.</td></tr>`;
        return;
      }

      tableBody.innerHTML = logs.map(l => `
        <tr>
          <td><span class="code-pill">${l.action}</span></td>
          <td>${l.actor_id || 'system'}</td>
          <td><pre style="font-size:0.75rem; color:var(--text-secondary); max-width:280px; overflow:auto;">${JSON.stringify(l.after || l.before || {}, null, 1)}</pre></td>
          <td style="font-size:0.8rem; color:var(--text-muted);">${new Date(l.created_at).toLocaleString()}</td>
        </tr>
      `).join('');
    } catch (err) {
      tableBody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--accent-rose);">Error: ${err.message}</td></tr>`;
    }
  },

  async loadPendingPolicyRuns() {
    const listEl = document.getElementById('admin-pending-policy-list');
    listEl.innerHTML = `<p style="color:var(--text-secondary);">Scanning LangGraph checkpoint states...</p>`;

    try {
      const items = await apiClient.getPendingPolicyReviews();
      if (!items || items.length === 0) {
        listEl.innerHTML = `<p style="color:var(--text-muted);">No policy runs awaiting human verification.</p>`;
        return;
      }

      listEl.innerHTML = items.map(it => `
        <div class="search-card" style="margin-bottom: 1rem; padding: 1.25rem;">
          <div style="display:flex; justify-content:space-between; margin-bottom:0.5rem;">
            <strong style="color:var(--accent-cyan);">Question: "${it.customer_question}"</strong>
            <span class="system-status-indicator"><span class="pulse-dot"></span> Pending Approval</span>
          </div>
          <p style="font-size:0.9rem; color:var(--text-secondary); margin-bottom:0.75rem; background:rgba(0,0,0,0.25); padding:0.75rem; border-radius:8px;">
            ${it.draft_answer}
          </p>
          <div style="display:flex; gap:0.5rem; justify-content:flex-end;">
            <button class="btn-primary" style="padding:0.4rem 1rem; font-size:0.82rem;" onclick="AdminController.approveRun('${it.run_id}')">Approve & Send</button>
            <button class="btn-danger" style="padding:0.4rem 1rem; font-size:0.82rem;" onclick="AdminController.rejectRun('${it.run_id}')">Reject</button>
          </div>
        </div>
      `).join('');
    } catch (err) {
      listEl.innerHTML = `<p style="color:var(--accent-rose);">Error loading reviews: ${err.message}</p>`;
    }
  },

  async approveRun(runId) {
    try {
      await apiClient.approvePolicyRun(runId);
      App.showToast('Policy answer approved and delivered to customer.', 'success');
      this.loadPendingPolicyRuns();
    } catch (err) {
      App.showToast(`Approval failed: ${err.message}`, 'error');
    }
  },

  async rejectRun(runId) {
    try {
      await apiClient.rejectPolicyRun(runId, 'Inaccurate policy summary');
      App.showToast('Policy draft rejected.', 'warning');
      this.loadPendingPolicyRuns();
    } catch (err) {
      App.showToast(`Rejection failed: ${err.message}`, 'error');
    }
  },

  async loadPendingCompensations() {
    const listEl = document.getElementById('admin-compensations-list');
    listEl.innerHTML = `<p style="color:var(--text-secondary);">Querying pending statutory compensation claims...</p>`;

    try {
      const claims = await apiClient.getPendingCompensations();
      if (!claims || claims.length === 0) {
        listEl.innerHTML = `<p style="color:var(--text-muted);">No compensation claims awaiting review.</p>`;
        return;
      }

      listEl.innerHTML = claims.map(c => `
        <div class="search-card" style="margin-bottom: 1rem; padding: 1.25rem;">
          <div style="display:flex; justify-content:space-between; margin-bottom:0.5rem; align-items: center;">
            <div>
              <strong style="color:var(--accent-amber); font-size:1.05rem;">Claim: ${c.claim_type.toUpperCase().replace('_', ' ')}</strong>
              <span class="code-pill" style="margin-left: 0.5rem;">${c.currency || 'USD'} ${c.amount}</span>
            </div>
            <span class="seat-status-pill status-low">● Requires Sign-off</span>
          </div>
          <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:0.75rem; background:rgba(0,0,0,0.25); padding:0.75rem; border-radius:8px;">
            <div><strong>Booking ID:</strong> ${c.booking_id}</div>
            <div><strong>Passenger ID:</strong> ${c.passenger_id}</div>
            <div><strong>Flight ID:</strong> ${c.flight_id}</div>
            <div><strong>Reason / Details:</strong> ${c.reason || 'Delayed > 3 hours or denied boarding'}</div>
          </div>
          <div style="display:flex; gap:0.5rem; justify-content:flex-end;">
            <button class="btn-primary" style="padding:0.4rem 1rem; font-size:0.82rem; background:var(--accent-emerald);" onclick="AdminController.approveCompensation('${c.claim_id}')">Approve Payout</button>
            <button class="btn-danger" style="padding:0.4rem 1rem; font-size:0.82rem;" onclick="AdminController.rejectCompensation('${c.claim_id}')">Reject Claim</button>
          </div>
        </div>
      `).join('');
    } catch (err) {
      listEl.innerHTML = `<p style="color:var(--accent-rose);">Error loading claims: ${err.message}</p>`;
    }
  },

  async approveCompensation(claimId) {
    try {
      await apiClient.reviewCompensation(claimId, 'approved', 'Super admin verified statutory delay / denied boarding');
      App.showToast('Compensation claim approved and payout scheduled.', 'success');
      this.loadPendingCompensations();
    } catch (err) {
      App.showToast(`Approval failed: ${err.message}`, 'error');
    }
  },

  async rejectCompensation(claimId) {
    const reason = prompt('Enter rejection reason for customer notification:', 'Flight disruption classified as extraordinary circumstances');
    if (!reason) return;
    try {
      await apiClient.reviewCompensation(claimId, 'rejected', reason);
      App.showToast('Compensation claim rejected.', 'warning');
      this.loadPendingCompensations();
    } catch (err) {
      App.showToast(`Rejection failed: ${err.message}`, 'error');
    }
  }
};

window.AdminController = AdminController;
