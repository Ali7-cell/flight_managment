/**
 * AeroFlow FMS - API Client
 * Connects directly to FastAPI backend (http://localhost:8000).
 * Automatically injects Idempotency-Key and Supabase JWT tokens.
 * Features realistic fallback simulation if backend is running offline.
 */

const API_CONFIG = {
  BASE_URL: (window.location.protocol.startsWith('http') && window.location.port === '8000')
    ? ''
    : 'http://localhost:8000',
  MOCK_FALLBACK: true, // Enables smooth demo data when backend is not running
};

function generateUUID() {
  if (crypto && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

const apiClient = {
  getAuthToken() {
    return localStorage.getItem('aeroflow_token') || null;
  },

  setAuthToken(token, user) {
    if (token) {
      localStorage.setItem('aeroflow_token', token);
      localStorage.setItem('aeroflow_user', JSON.stringify(user || {}));
    } else {
      localStorage.removeItem('aeroflow_token');
      localStorage.removeItem('aeroflow_user');
    }
  },

  getCurrentUser() {
    try {
      return JSON.parse(localStorage.getItem('aeroflow_user') || '{}');
    } catch {
      return {};
    }
  },

  async request(endpoint, options = {}) {
    const url = `${API_CONFIG.BASE_URL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const token = this.getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (options.requiresIdempotency && !headers['Idempotency-Key']) {
      headers['Idempotency-Key'] = generateUUID();
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        let errDetail = 'Request failed';
        try {
          const errData = await response.json();
          errDetail = errData.detail || errData.message || JSON.stringify(errData);
        } catch {
          errDetail = response.statusText;
        }
        throw new Error(errDetail);
      }

      return await response.json();
    } catch (error) {
      // If network fails (backend offline) and fallback is allowed:
      if (API_CONFIG.MOCK_FALLBACK && (error.message.includes('Failed to fetch') || error.message.includes('NetworkError'))) {
        console.warn(`[AeroFlow] Backend offline at ${url}, executing mock fallback.`);
        return this.mockHandler(endpoint, options);
      }
      throw error;
    }
  },

  // --- API Endpoint Methods ---

  async checkHealth() {
    try {
      const res = await fetch(`${API_CONFIG.BASE_URL}/healthz`, { method: 'GET' });
      return res.ok;
    } catch {
      return false;
    }
  },

  async searchFlights(origin, destination, departureDate, currency = 'USD') {
    let query = `?origin=${encodeURIComponent(origin.toUpperCase())}&destination=${encodeURIComponent(destination.toUpperCase())}&currency=${encodeURIComponent(currency)}`;
    if (departureDate) query += `&departure_date=${encodeURIComponent(departureDate)}`;
    return this.request(`/search/flights${query}`, { method: 'GET' });
  },

  async searchConnecting(origin, destination, departureDate, currency = 'USD') {
    let query = `?origin=${encodeURIComponent(origin.toUpperCase())}&destination=${encodeURIComponent(destination.toUpperCase())}&currency=${encodeURIComponent(currency)}`;
    if (departureDate) query += `&departure_date=${encodeURIComponent(departureDate)}`;
    return this.request(`/search/connecting${query}`, { method: 'GET' });
  },

  async getSeatMap(flightId) {
    return this.request(`/flights/${flightId}/seat-map`, { method: 'GET' });
  },

  async holdSeats(flightId, seatClassId, quantity, passengerEmail, passengerName, seatNumber = null) {
    return this.request('/bookings/hold', {
      method: 'POST',
      requiresIdempotency: true,
      body: JSON.stringify({
        flight_id: flightId,
        seat_class_id: seatClassId,
        quantity: quantity || 1,
        passenger_email: passengerEmail,
        passenger_name: passengerName,
        seat_number: seatNumber,
      }),
    });
  },

  async confirmBooking(holdId, paymentMethodId = 'pm_card_visa') {
    return this.request(`/bookings/${holdId}/confirm`, {
      method: 'POST',
      requiresIdempotency: true,
      body: JSON.stringify({
        payment_method_id: paymentMethodId,
      }),
    });
  },

  async getBooking(bookingId) {
    return this.request(`/bookings/${bookingId}`, { method: 'GET' });
  },

  async cancelBooking(bookingId, reason = 'Customer request') {
    return this.request(`/bookings/${bookingId}/cancel`, {
      method: 'POST',
      requiresIdempotency: true,
      body: JSON.stringify({ reason }),
    });
  },

  async cancelPartialBooking(bookingId, seatsToCancel, reason = 'Partial cancellation') {
    return this.request(`/bookings/${bookingId}/cancel-partial`, {
      method: 'POST',
      requiresIdempotency: true,
      body: JSON.stringify({
        seats_to_cancel: parseInt(seatsToCancel, 10),
        reason,
      }),
    });
  },

  async resolveCancellation(bookingId, resolutionChoice, targetFlightId = null) {
    return this.request(`/bookings/${bookingId}/resolution`, {
      method: 'POST',
      body: JSON.stringify({
        resolution_choice: resolutionChoice,
        target_flight_id: targetFlightId,
      }),
    });
  },

  async submitCompensation(payload) {
    return this.request('/bookings/compensation/claim', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getPendingCompensations() {
    return this.request('/admin/compensation/pending', { method: 'GET' });
  },

  async reviewCompensation(claimId, action, notes = null) {
    return this.request(`/admin/compensation/${claimId}/review`, {
      method: 'POST',
      body: JSON.stringify({ action, notes }),
    });
  },

  async joinWaitlist(flightId, seatClassId, quantity, passengerEmail, passengerName) {
    return this.request('/waitlist', {
      method: 'POST',
      requiresIdempotency: true,
      body: JSON.stringify({
        flight_id: flightId,
        seat_class_id: seatClassId,
        quantity: quantity || 1,
        passenger_email: passengerEmail,
        passenger_name: passengerName,
      }),
    });
  },

  async getWaitlistPosition(flightId, waitlistEntryId) {
    let q = waitlistEntryId ? `?waitlist_entry_id=${waitlistEntryId}` : '';
    return this.request(`/waitlist/${flightId}/position${q}`, { method: 'GET' });
  },

  async submitPolicyQuestion(question, bookingId = null) {
    return this.request('/policy/questions', {
      method: 'POST',
      body: JSON.stringify({
        question,
        booking_id: bookingId,
      }),
    });
  },

  async getPendingPolicyReviews() {
    return this.request('/internal/policy/pending', { method: 'GET' });
  },

  async approvePolicyRun(runId, editedAnswer = null) {
    return this.request(`/internal/policy/${runId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ edited_answer: editedAnswer }),
    });
  },

  async rejectPolicyRun(runId, reason = 'Not aligned with airline policy') {
    return this.request(`/internal/policy/${runId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  },

  async adminCreateFlight(payload) {
    return this.request('/admin/flights', {
      method: 'POST',
      requiresIdempotency: true,
      body: JSON.stringify(payload),
    });
  },

  async adminResizeSeatClass(flightId, className, newTotalSeats) {
    return this.request(`/admin/flights/${flightId}/seat-classes`, {
      method: 'PATCH',
      requiresIdempotency: true,
      body: JSON.stringify({
        class_name: className,
        new_total_seats: parseInt(newTotalSeats, 10),
      }),
    });
  },

  async adminGetAuditLog(flightId) {
    return this.request(`/admin/flights/${flightId}/audit-log`, { method: 'GET' });
  },

  async login(email, password) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  async signup(email, fullName, password) {
    return this.request('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, full_name: fullName, password }),
    });
  },

  // --- Realistic Mock Data Handler (for offline testing) ---
  mockHandler(endpoint, options) {
    const url = endpoint.split('?')[0];

    if (url.includes('/search/flights')) {
      return [
        {
          flight_id: 'a1b2c3d4-e5f6-7a8b-9c0d-112233445566',
          flight_number: 'AF-204',
          airline: 'AeroFlow Airlines',
          origin: 'JFK',
          destination: 'LHR',
          origin_tz: 'America/New_York',
          destination_tz: 'Europe/London',
          departure_local: '2026-09-10T18:30:00',
          arrival_local: '2026-09-11T06:45:00',
          duration_minutes: 435,
          seat_classes: [
            { id: 'sc-eco-1', class_name: 'economy', price: 480.00, total_seats: 120, booked_seats: 112, held_seats: 3, available_seats: 5 },
            { id: 'sc-biz-1', class_name: 'business', price: 1250.00, total_seats: 30, booked_seats: 28, held_seats: 1, available_seats: 1 },
            { id: 'sc-fst-1', class_name: 'first', price: 2900.00, total_seats: 8, booked_seats: 8, held_seats: 0, available_seats: 0 }
          ]
        },
        {
          flight_id: 'b2c3d4e5-f6a7-8b9c-0d1e-223344556677',
          flight_number: 'AF-809',
          airline: 'AeroFlow Sky Express',
          origin: 'JFK',
          destination: 'LHR',
          origin_tz: 'America/New_York',
          destination_tz: 'Europe/London',
          departure_local: '2026-09-10T22:00:00',
          arrival_local: '2026-09-11T10:15:00',
          duration_minutes: 435,
          seat_classes: [
            { id: 'sc-eco-2', class_name: 'economy', price: 520.00, total_seats: 150, booked_seats: 80, held_seats: 5, available_seats: 65 },
            { id: 'sc-biz-2', class_name: 'business', price: 1400.00, total_seats: 25, booked_seats: 12, held_seats: 0, available_seats: 13 }
          ]
        }
      ];
    }

    if (url.includes('/bookings/hold')) {
      const body = JSON.parse(options.body || '{}');
      const holdExpires = new Date(Date.now() + 10 * 60 * 1000).toISOString();
      return {
        hold_id: generateUUID(),
        flight_id: body.flight_id,
        seat_class_id: body.seat_class_id,
        quantity: body.quantity || 1,
        expires_at: holdExpires,
        passenger_name: body.passenger_name || 'Muhammad Ali',
        passenger_email: body.passenger_email || 'ali@example.com'
      };
    }

    if (url.includes('/confirm')) {
      return {
        booking_id: generateUUID(),
        pnr: 'AF' + Math.floor(1000 + Math.random() * 9000),
        status: 'confirmed',
        passenger_name: 'Muhammad Ali',
        passenger_email: 'ali@example.com',
        flight_number: 'AF-204',
        origin: 'JFK',
        destination: 'LHR',
        class_name: 'economy',
        seat_number: '14B',
        created_at: new Date().toISOString()
      };
    }

    if (url.includes('/waitlist') && options.method === 'POST') {
      return {
        waitlist_entry_id: generateUUID(),
        position: 1,
        status: 'waiting',
        message: 'You have been added to the priority waitlist.'
      };
    }

    if (url.includes('/position')) {
      return {
        position: 1,
        status: 'waiting',
        estimated_chance: 'High'
      };
    }

    if (url.includes('/policy/questions')) {
      const body = JSON.parse(options.body || '{}');
      return {
        run_id: generateUUID(),
        status: 'pending_approval',
        draft_answer: `According to AeroFlow fare regulations, Economy Standard tickets can be canceled with a $50 administrative fee up to 24 hours prior to scheduled departure. Business and First Class fares are 100% refundable.`,
        consistency_flags: ['Verified against Fare Matrix (Grounding 100%)']
      };
    }

    if (url.includes('/auth/login') || url.includes('/auth/signup')) {
      const body = JSON.parse(options.body || '{}');
      return {
        access_token: 'mock-jwt-token-' + generateUUID(),
        user_id: generateUUID(),
        role: body.email.includes('admin') ? 'super_admin' : 'customer'
      };
    }

    return { status: 'mock_success', endpoint: url };
  }
};

window.apiClient = apiClient;
