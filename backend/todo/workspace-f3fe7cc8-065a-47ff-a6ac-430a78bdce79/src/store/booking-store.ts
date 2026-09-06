"use client";

import { create } from "zustand";
import type { Airport, Booking, Flight, SearchQuery, Seat, BookingStep } from "@/lib/types";

interface BookingState {
  // Search query + results
  query: SearchQuery;
  setQuery: (q: Partial<SearchQuery>) => void;

  // Results
  flights: Flight[];
  resultsLoading: boolean;
  setFlights: (f: Flight[]) => void;
  setResultsLoading: (b: boolean) => void;

  // Step in the booking wizard
  step: BookingStep;
  setStep: (s: BookingStep) => void;

  // Currently selected flight + seats
  selectedFlight: Flight | null;
  selectFlight: (f: Flight) => void;
  seats: Seat[];
  setSeats: (s: Seat[]) => void;
  selectedSeat: Seat | null;
  selectSeat: (s: Seat | null) => void;

  // Passenger
  passenger: {
    name: string;
    email: string;
    phone: string;
  };
  setPassenger: (p: Partial<{ name: string; email: string; phone: string }>) => void;

  // Payment
  payment: {
    cardName: string;
    cardNumber: string;
    expiry: string;
    cvc: string;
    method: "card" | "wallet" | "paypal";
  };
  setPayment: (p: Partial<{ cardName: string; cardNumber: string; expiry: string; cvc: string; method: "card" | "wallet" | "paypal" }>) => void;

  // Booking result
  booking: Booking | null;
  setBooking: (b: Booking | null) => void;

  // Reset to start
  reset: () => void;
}

const today = () => {
  const d = new Date();
  d.setDate(d.getDate() + 3);
  return d.toISOString().split("T")[0];
};

const defaultQuery: SearchQuery = {
  from: "JFK",
  to: "LHR",
  date: today(),
  passengers: 1,
  cabin: "economy",
};

export const useBookingStore = create<BookingState>((set) => ({
  query: defaultQuery,
  setQuery: (q) => set((s) => ({ query: { ...s.query, ...q } })),

  flights: [],
  resultsLoading: false,
  setFlights: (f) => set({ flights: f }),
  setResultsLoading: (b) => set({ resultsLoading: b }),

  step: "search",
  setStep: (s) => set({ step: s }),

  selectedFlight: null,
  selectFlight: (f) => set({ selectedFlight: f }),
  seats: [],
  setSeats: (s) => set({ seats: s }),
  selectedSeat: null,
  selectSeat: (s) => set({ selectedSeat: s }),

  passenger: { name: "", email: "", phone: "" },
  setPassenger: (p) => set((s) => ({ passenger: { ...s.passenger, ...p } })),

  payment: { cardName: "", cardNumber: "", expiry: "", cvc: "", method: "card" },
  setPayment: (p) => set((s) => ({ payment: { ...s.payment, ...p } })),

  booking: null,
  setBooking: (b) => set({ booking: b }),

  reset: () =>
    set({
      step: "search",
      flights: [],
      selectedFlight: null,
      seats: [],
      selectedSeat: null,
      passenger: { name: "", email: "", phone: "" },
      payment: { cardName: "", cardNumber: "", expiry: "", cvc: "", method: "card" },
      booking: null,
    }),
}));

// Helper hook for airport search
export function useAirportSearch() {
  return {
    search: async (q: string): Promise<Airport[]> => {
      const url = `/api/airports?q=${encodeURIComponent(q)}&limit=20`;
      const r = await fetch(url);
      if (!r.ok) return [];
      const data = await r.json();
      return data.airports || [];
    },
  };
}
