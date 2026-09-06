import { CabinClass, Flight, Seat } from "./types";

// Format currency
export function formatMoney(value: number, currency = "USD") {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

// Format a short time like "10:35 AM"
export function formatTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

// Format a short date like "Mon, Sep 10"
export function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

// Format a long date like "September 10, 2026"
export function formatDateLong(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

// Duration like "5h 25m"
export function formatDuration(min: number) {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `${h}h ${m.toString().padStart(2, "0")}m`;
}

// Cabin display
export function cabinLabel(c: CabinClass) {
  if (c === "first") return "First";
  if (c === "business") return "Business";
  return "Economy";
}

// Price for a flight given a cabin
export function priceForCabin(flight: Flight, cabin: CabinClass) {
  if (cabin === "first") return flight.priceFirst;
  if (cabin === "business") return flight.priceBusiness;
  return flight.priceEconomy;
}

// Build a 2D grid of seats for a flight (rows × columns).
export function seatsToGrid(seats: Seat[]) {
  const cols = ["A", "B", "C", "D", "E", "F"];
  const rowsMap = new Map<number, Seat[]>();
  for (const s of seats) {
    if (!rowsMap.has(s.row)) rowsMap.set(s.row, []);
    rowsMap.get(s.row)!.push(s);
  }
  const rows = Array.from(rowsMap.keys()).sort((a, b) => a - b);
  const grid = rows.map((r) => {
    const rowSeats = rowsMap.get(r)!;
    const cells = cols.map((c) => rowSeats.find((s) => s.column === c) || null);
    return { row: r, cells };
  });
  return grid;
}

// Count available seats by cabin
export function countByCabin(seats: Seat[]) {
  const totals = { economy: 0, business: 0, first: 0 } as Record<CabinClass, number>;
  const available = { economy: 0, business: 0, first: 0 } as Record<CabinClass, number>;
  for (const s of seats) {
    totals[s.cabinClass]++;
    if (s.isAvailable) available[s.cabinClass]++;
  }
  return { totals, available };
}
