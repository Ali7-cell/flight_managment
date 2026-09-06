// Shared types for the Skyway flight-booking frontend.

export type CabinClass = "economy" | "business" | "first";

export interface Airport {
  code: string;
  name: string;
  city: string;
  country: string;
  region: string;
  lat: number;
  lng: number;
  timezone: string;
}

export interface Flight {
  id: string;
  flightNumber: string;
  airline: string;
  airlineCode: string;
  fromCode: string;
  toCode: string;
  fromAirport: Airport;
  toAirport: Airport;
  departureTime: string; // ISO
  arrivalTime: string;   // ISO
  durationMin: number;
  aircraft: string;
  totalSeats: number;
  availableSeats: number;
  priceEconomy: number;
  priceBusiness: number;
  priceFirst: number;
  status: string;
  gate?: string | null;
}

export interface Seat {
  id: string;
  flightId: string;
  seatNumber: string;
  cabinClass: CabinClass;
  row: number;
  column: string;
  isAvailable: boolean;
  price: number;
}

export interface Booking {
  id: string;
  reference: string;
  flightId: string;
  flight?: Flight;
  seatNumber: string;
  cabinClass: CabinClass;
  passengerName: string;
  passengerEmail: string;
  passengerPhone?: string | null;
  totalAmount: number;
  currency: string;
  status: string;
  paymentMethod?: string | null;
  paymentStatus: string;
  createdAt: string;
}

export type BookingStep =
  | "search"
  | "results"
  | "seats"
  | "passenger"
  | "payment"
  | "confirmation";

export interface SearchQuery {
  from: string;
  to: string;
  date: string;        // YYYY-MM-DD
  passengers: number;
  cabin: CabinClass;
}
