/**
 * AeroFlow FMS - Booking & Search Engine Controller
 */

const BookingController = {
  activeHold: null,
  holdTimerInterval: null,

  init() {
    this.bindEvents();
    this.checkStoredHold();
  },

  bindEvents() {
    const searchForm = document.getElementById('flight-search-form');
    if (searchForm) {
      searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.performSearch();
      });
    }

    // Quick route chip buttons
    document.querySelectorAll('.route-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const [from, to] = chip.dataset.route.split('-');
        document.getElementById('search-origin').value = from;
        document.getElementById('search-destination').value = to;
        this.performSearch();
      });
    });

    // Checkout modal form submit
    const checkoutForm = document.getElementById('checkout-form');
    if (checkoutForm) {
      checkoutForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.confirmHoldCheckout();
      });
    }

    // PNR lookup form
    const lookupForm = document.getElementById('booking-lookup-form');
    if (lookupForm) {
      lookupForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.lookupBooking();
      });
    }
  },

  async performSearch() {
    const origin = document.getElementById('search-origin').value.trim();
    const destination = document.getElementById('search-destination').value.trim();
    const departureDate = document.getElementById('search-date').value;

    if (!origin || !destination) {
      App.showToast('Please enter both Origin and Destination 3-letter IATA codes', 'warning');
      return;
    }

    const container = document.getElementById('flights-results-container');
    container.innerHTML = `
      <div style="text-align: center; padding: 3rem; color: var(--text-secondary);">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">✈️</div>
        Scanning airline inventory & real-time seat availability...
      </div>
    `;

    try {
      const flights = await apiClient.searchFlights(origin, destination, departureDate);
      this.renderFlights(flights);
    } catch (err) {
      container.innerHTML = `
        <div style="text-align: center; padding: 2rem; color: var(--accent-rose);">
          <p>Failed to retrieve flights: ${err.message}</p>
        </div>
      `;
      App.showToast(err.message, 'error');
    }
  },

  renderFlights(flights) {
    const container = document.getElementById('flights-results-container');
    if (!flights || flights.length === 0) {
      container.innerHTML = `
        <div class="search-card" style="text-align: center; padding: 3rem;">
          <p style="color: var(--text-secondary); margin-bottom: 1rem;">No direct flights scheduled for this route & date.</p>
          <button class="btn-secondary" onclick="document.getElementById('search-date').value=''; BookingController.performSearch();">View All Scheduled Dates</button>
        </div>
      `;
      return;
    }

    let html = `
      <div class="results-header">
        <span class="results-count">Available Departures (${flights.length})</span>
        <span style="font-size: 0.85rem; color: var(--text-muted);">Real-time inventory locks enforced</span>
      </div>
      <div class="flights-list">
    `;

    flights.forEach(f => {
      const rawDep = f.departure_at || f.departure_local;
      const rawArr = f.arrival_at || f.arrival_local;
      const depDateObj = rawDep ? new Date(rawDep) : new Date();
      const arrDateObj = rawArr ? new Date(rawArr) : new Date();

      const depTime = rawDep ? depDateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }) : '10:00';
      const arrTime = rawArr ? arrDateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }) : '18:15';
      const depDateStr = rawDep ? depDateObj.toLocaleDateString([], { month: 'short', day: 'numeric' }) : '';

      const diffMinutes = Math.max(60, Math.round((arrDateObj - depDateObj) / (1000 * 60)));
      const durationHours = Math.floor(diffMinutes / 60);
      const durationMins = diffMinutes % 60;

      const lowestPrice = (f.seat_classes && f.seat_classes[0]) 
        ? parseFloat(f.seat_classes[0].fare_base_amount || f.seat_classes[0].price || 350).toFixed(0)
        : '350';

      html += `
        <div class="flight-card" data-flight-id="${f.flight_id}">
          <div class="flight-card-main">
            <div class="airline-badge-col">
              <span class="flight-number-tag">${f.flight_number}</span>
              <span class="airline-name">${f.airline || 'AeroFlow Airlines'}</span>
              ${depDateStr ? `<span style="font-size: 0.72rem; color: var(--accent-cyan);">📅 ${depDateStr}</span>` : ''}
            </div>

            <div class="route-timeline-col">
              <div class="route-point">
                <div class="route-time">${depTime}</div>
                <div class="route-code">${f.origin}</div>
                <div class="route-tz">${f.origin_tz || 'UTC'}</div>
              </div>

              <div class="route-flightpath">
                <span class="flight-duration">${durationHours}h ${durationMins}m</span>
                <div class="flight-path-line">
                  <span class="flight-path-plane">✈</span>
                </div>
                <span style="font-size: 0.7rem; color: var(--accent-emerald);">Non-stop</span>
              </div>

              <div class="route-point">
                <div class="route-time">${arrTime}</div>
                <div class="route-code">${f.destination}</div>
                <div class="route-tz">${f.destination_tz || 'UTC'}</div>
              </div>
            </div>

            <div style="text-align: right;">
              <span style="font-size: 0.75rem; color: var(--text-muted); display: block;">Starting from</span>
              <span style="font-size: 1.4rem; font-weight: 800; color: var(--accent-cyan);">$${lowestPrice}</span>
            </div>
          </div>

          <div class="flight-seat-classes">
      `;

      (f.seat_classes || []).forEach(sc => {
        const scId = sc.seat_class_id || sc.id;
        const price = parseFloat(sc.fare_base_amount || sc.price || 350).toFixed(0);
        const available = (sc.available_seats !== undefined) 
          ? sc.available_seats 
          : Math.max(0, sc.total_seats - ((sc.booked_seats || 0) + (sc.held_seats || 0)));

        const isSoldOut = available <= 0;
        const statusClass = isSoldOut ? 'status-full' : (available <= 5 ? 'status-low' : 'status-available');
        const statusText = isSoldOut ? 'Sold Out' : (available <= 5 ? `Only ${available} Left!` : `${available} Available`);

        html += `
          <div class="seat-class-box ${isSoldOut ? 'sold-out' : ''}">
            <div>
              <div class="seat-class-header">
                <span class="seat-class-name">${sc.class_name}</span>
                <span class="seat-class-price">$${price}</span>
              </div>
              <span class="seat-status-pill ${statusClass}" style="margin-top: 0.4rem;">
                ● ${statusText}
              </span>
            </div>

            ${isSoldOut 
              ? `<button class="btn-waitlist" onclick="WaitlistController.openWaitlistModal('${f.flight_id}', '${scId}', '${f.flight_number}', '${sc.class_name}')">
                  Join Priority Waitlist
                 </button>`
              : `<button class="btn-hold-seat" onclick="BookingController.startSeatHold('${f.flight_id}', '${scId}', '${f.flight_number}', '${sc.class_name}', ${price}, '${f.origin}', '${f.destination}')">
                  Hold & Reserve
                 </button>`
            }
          </div>
        `;
      });


      html += `
          </div>
        </div>
      `;
    });

    html += `</div>`;
    container.innerHTML = html;
  },

  async startSeatHold(flightId, seatClassId, flightNumber, className, price, origin = 'JFK', destination = 'LHR') {
    const user = apiClient.getCurrentUser();
    const passengerEmail = user.email || prompt('Enter passenger email address:', 'passenger@example.com');
    if (!passengerEmail) return;

    const passengerName = user.full_name || 'Muhammad Ali';

    try {
      App.showToast('Securing seat hold with atomic lock...', 'info');
      const holdRes = await apiClient.holdSeats(flightId, seatClassId, 1, passengerEmail, passengerName);
      
      this.activeHold = {
        ...holdRes,
        flightNumber,
        className,
        price,
        origin,
        destination,
        passengerEmail,
        passengerName,
        expiresAt: new Date(Date.now() + 10 * 60 * 1000).getTime()
      };

      localStorage.setItem('aeroflow_active_hold', JSON.stringify(this.activeHold));
      this.renderHoldBanner();
      this.openCheckoutModal();
      App.showToast('Seat held for 10 minutes! Please confirm payment.', 'success');
    } catch (err) {
      App.showToast(`Seat hold failed: ${err.message}`, 'error');
    }
  },

  checkStoredHold() {
    const stored = localStorage.getItem('aeroflow_active_hold');
    if (stored) {
      try {
        this.activeHold = JSON.parse(stored);
        if (Date.now() < this.activeHold.expiresAt) {
          this.renderHoldBanner();
        } else {
          this.clearHold();
        }
      } catch {
        this.clearHold();
      }
    }
  },

  renderHoldBanner() {
    const banner = document.getElementById('active-hold-banner');
    if (!banner || !this.activeHold) return;

    banner.style.display = 'flex';
    clearInterval(this.holdTimerInterval);

    const updateTimer = () => {
      const remainingSec = Math.max(0, Math.floor((this.activeHold.expiresAt - Date.now()) / 1000));
      const mins = Math.floor(remainingSec / 60);
      const secs = remainingSec % 60;
      const clockStr = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

      const clockEl = document.getElementById('hold-timer-display');
      if (clockEl) clockEl.innerText = clockStr;

      if (remainingSec <= 0) {
        clearInterval(this.holdTimerInterval);
        App.showToast('Seat hold has expired. Seat returned to inventory.', 'warning');
        this.clearHold();
      }
    };

    updateTimer();
    this.holdTimerInterval = setInterval(updateTimer, 1000);
  },

  clearHold() {
    this.activeHold = null;
    clearInterval(this.holdTimerInterval);
    localStorage.removeItem('aeroflow_active_hold');
    const banner = document.getElementById('active-hold-banner');
    if (banner) banner.style.display = 'none';
  },

  openCheckoutModal() {
    if (!this.activeHold) return;
    document.getElementById('checkout-flight-badge').innerText = `${this.activeHold.flightNumber} • ${this.activeHold.className.toUpperCase()}`;
    document.getElementById('checkout-total-price').innerText = `$${this.activeHold.price}`;
    document.getElementById('checkout-passenger-name').value = this.activeHold.passengerName;
    document.getElementById('checkout-passenger-email').value = this.activeHold.passengerEmail;
    App.openModal('checkout-modal');
  },

  async confirmHoldCheckout() {
    if (!this.activeHold) {
      App.showToast('No active seat hold found.', 'error');
      return;
    }

    const btn = document.getElementById('btn-confirm-checkout');
    btn.disabled = true;
    btn.innerText = 'Processing Payment...';

    try {
      const confirmRes = await apiClient.confirmBooking(this.activeHold.hold_id);
      App.closeModal('checkout-modal');
      const pnr = confirmRes.booking_reference || confirmRes.pnr || 'AF' + Math.floor(1000 + Math.random() * 9000);
      
      const bookingData = {
        ...confirmRes,
        pnr: pnr,
        passenger_name: this.activeHold.passengerName,
        passenger_email: this.activeHold.passengerEmail,
        flight_number: this.activeHold.flightNumber,
        origin: this.activeHold.origin,
        destination: this.activeHold.destination,
        class_name: this.activeHold.className,
      };

      this.clearHold();
      App.showToast(`Booking Confirmed! PNR: ${pnr}`, 'success');
      this.renderBoardingPass(bookingData);
      App.switchTab('tab-my-bookings');
    } catch (err) {
      App.showToast(`Payment Confirmation Failed: ${err.message}`, 'error');
    } finally {
      btn.disabled = false;
      btn.innerText = 'Pay & Issue Ticket';
    }
  },

  renderBoardingPass(booking) {
    const container = document.getElementById('boarding-pass-display-area');
    if (!container) return;

    const pnr = booking.booking_reference || booking.pnr || 'AF' + Math.floor(1000 + Math.random() * 9000);
    const passName = booking.passenger_name || (this.activeHold && this.activeHold.passengerName) || 'Muhammad Ali';
    const flightNum = booking.flight_number || (this.activeHold && this.activeHold.flightNumber) || 'AF-204';
    const origin = booking.origin || (this.activeHold && this.activeHold.origin) || 'JFK';
    const dest = booking.destination || (this.activeHold && this.activeHold.destination) || 'LHR';
    const cls = booking.class_name || (this.activeHold && this.activeHold.className) || 'Economy';

    container.innerHTML = `
      <div class="boarding-pass-card">
        <div class="pass-header">
          <div class="pass-brand">✈ AEROFLOW AIRLINES</div>
          <div class="pass-pnr-tag">PNR: ${pnr}</div>
        </div>

        <div class="pass-body">
          <div class="pass-route-row">
            <div>
              <div class="pass-city-code">${origin}</div>
              <div class="pass-city-label">Departure Airport</div>
            </div>
            <div style="color: var(--accent-cyan); font-size: 1.5rem;">✈ ─────── ✈</div>
            <div style="text-align: right;">
              <div class="pass-city-code">${dest}</div>
              <div class="pass-city-label">Arrival Airport</div>
            </div>
          </div>

          <div class="pass-details-grid">
            <div class="pass-detail-item">
              <span class="detail-label">Passenger</span>
              <span class="detail-val">${passName}</span>
            </div>
            <div class="pass-detail-item">
              <span class="detail-label">Flight</span>
              <span class="detail-val">${flightNum}</span>
            </div>
            <div class="pass-detail-item">
              <span class="detail-label">Class / Seat</span>
              <span class="detail-val">${cls.toUpperCase()} / 14B</span>
            </div>
            <div class="pass-detail-item">
              <span class="detail-label">Gate</span>
              <span class="detail-val">B-12</span>
            </div>
          </div>
        </div>

        <div class="pass-perforation">
          <div class="pass-dash-line"></div>
        </div>

        <div class="pass-footer">
          <div>
            <span style="font-size: 0.75rem; color: #64748b; display: block;">Status: <strong>Confirmed & Ticketed</strong></span>
            <span style="font-size: 0.7rem; color: #10b981;">Check-in open 24h before departure</span>
          </div>
          <div class="mock-barcode"></div>
        </div>
      </div>

      <div style="display: flex; justify-content: center; gap: 0.75rem; margin-top: 1rem; flex-wrap: wrap;">
        <button class="btn-primary" onclick="window.print()">Print / Save Boarding Pass</button>
        <button class="btn-secondary" onclick="BookingController.promptPartialCancel('${booking.booking_id}', ${booking.quantity || 1})">Cancel Partial Seat</button>
        <button class="btn-danger" onclick="BookingController.cancelCurrentBooking('${booking.booking_id}')">Cancel Entire Booking</button>
        <button class="btn-secondary" style="border-color: var(--accent-amber); color: var(--accent-amber);" onclick="BookingController.promptCompensationClaim('${booking.booking_id}', '${booking.flight_id || ''}')">File Compensation Claim</button>
        <button class="btn-secondary" style="border-color: var(--accent-cyan); color: var(--accent-cyan);" onclick="BookingController.promptResolution('${booking.booking_id}')">Flight Disruption Resolution</button>
      </div>
    `;
  },

  async lookupBooking() {
    const input = document.getElementById('lookup-pnr-input').value.trim();
    if (!input) return;

    App.showToast('Locating itinerary...', 'info');
    try {
      const res = await apiClient.getBooking(input);
      this.renderBoardingPass(res);
      App.showToast('Booking record found!', 'success');
    } catch (err) {
      App.showToast(`Lookup failed: ${err.message}`, 'error');
    }
  },

  async cancelCurrentBooking(bookingId) {
    if (!confirm('Are you sure you want to cancel this booking? This will immediately release your seat to waitlisted passengers.')) {
      return;
    }

    try {
      App.showToast('Releasing seat and initiating refund...', 'info');
      await apiClient.cancelBooking(bookingId, 'Customer cancellation');
      App.showToast('Booking successfully canceled and seat released.', 'success');
      document.getElementById('boarding-pass-display-area').innerHTML = `
        <div style="text-align: center; padding: 2rem; color: var(--accent-rose);">
          Booking has been cancelled. Seat was automatically promoted to the next passenger in waitlist.
        </div>
      `;
    } catch (err) {
      App.showToast(`Cancellation error: ${err.message}`, 'error');
    }
  },

  async promptPartialCancel(bookingId, currentSeats) {
    const countStr = prompt(`How many seats would you like to cancel? (Total booked: ${currentSeats})`, '1');
    if (!countStr) return;
    const count = parseInt(countStr, 10);
    if (isNaN(count) || count <= 0 || count >= currentSeats) {
      App.showToast(`Invalid quantity. Must be between 1 and ${currentSeats - 1}. For full cancellation, use Cancel Entire Booking.`, 'warning');
      return;
    }

    try {
      App.showToast(`Cancelling ${count} seat(s) and restocking inventory...`, 'info');
      const res = await apiClient.cancelPartialBooking(bookingId, count, 'Passenger partial cancellation');
      App.showToast(`Successfully cancelled ${count} seat(s). Refund: $${res.refund_amount || 0}`, 'success');
      this.lookupBooking();
    } catch (err) {
      App.showToast(`Partial cancellation failed: ${err.message}`, 'error');
    }
  },

  async promptCompensationClaim(bookingId, flightId) {
    const reason = prompt('Describe the disruption reason (e.g. Schedule delay >3h or Denied Boarding):', 'Flight delayed over 3 hours');
    if (!reason) return;
    const amountStr = prompt('Enter claim amount requested (USD):', '600');
    if (!amountStr) return;

    try {
      App.showToast('Submitting statutory compensation claim to Ops Desk...', 'info');
      const payload = {
        booking_id: bookingId,
        flight_id: flightId,
        passenger_id: (apiClient.getCurrentUser() && apiClient.getCurrentUser().id) || '00000000-0000-0000-0000-000000000001',
        claim_type: reason.toLowerCase().includes('denied') ? 'denied_boarding' : 'schedule_change',
        amount: parseFloat(amountStr) || 600,
        currency: 'USD',
        reason: reason
      };
      const res = await apiClient.submitCompensation(payload);
      App.showToast(`Claim submitted! Status: ${res.status}. Claim ID: ${res.claim_id}`, 'success');
    } catch (err) {
      App.showToast(`Claim submission failed: ${err.message}`, 'error');
    }
  },

  async promptResolution(bookingId) {
    const choice = prompt('Select Disruption Resolution Choice:\n1: 100% Cash Refund (enter "refund")\n2: 1-Year Travel Credit with bonus (enter "travel_credit")\n3: Free Rebooking (enter "rebook")', 'refund');
    if (!choice) return;

    let targetFlightId = null;
    if (choice.trim().toLowerCase() === 'rebook') {
      targetFlightId = prompt('Enter Target Flight UUID for free rebooking:');
      if (!targetFlightId) return;
    }

    try {
      App.showToast('Applying disruption resolution...', 'info');
      const res = await apiClient.resolveCancellation(bookingId, choice.trim().toLowerCase(), targetFlightId);
      App.showToast(`Resolution applied: ${res.status || 'Resolved'}! Details: ${JSON.stringify(res.resolution || res)}`, 'success');
      this.lookupBooking();
    } catch (err) {
      App.showToast(`Resolution failed: ${err.message}`, 'error');
    }
  }
};

window.BookingController = BookingController;
