/**
 * Skyway — flight-booking backend seed.
 * Run with: `bun run scripts/seed.ts`
 *
 * Seeds ~20 airports, ~36 flights (next 14 days), and ~24 seats per flight.
 * Idempotent: clears existing rows before re-seeding.
 */
import { PrismaClient } from "@prisma/client";

const db = new PrismaClient();

type AirportSeed = {
  code: string; name: string; city: string; country: string;
  region: string; lat: number; lng: number; timezone: string;
};

const AIRPORTS: AirportSeed[] = [
  { code: "JFK", name: "John F. Kennedy International",  city: "New York",       country: "United States",  region: "North America", lat: 40.6413, lng: -73.7781, timezone: "America/New_York" },
  { code: "LAX", name: "Los Angeles International",      city: "Los Angeles",    country: "United States",  region: "North America", lat: 33.9416, lng: -118.4085, timezone: "America/Los_Angeles" },
  { code: "SFO", name: "San Francisco International",   city: "San Francisco",   country: "United States",  region: "North America", lat: 37.6213, lng: -122.379, timezone: "America/Los_Angeles" },
  { code: "ORD", name: "O'Hare International",           city: "Chicago",         country: "United States",  region: "North America", lat: 41.9742, lng: -87.9073, timezone: "America/Chicago" },
  { code: "MIA", name: "Miami International",            city: "Miami",          country: "United States",  region: "North America", lat: 25.7959, lng: -80.2870, timezone: "America/New_York" },
  { code: "SEA", name: "Seattle-Tacoma International",   city: "Seattle",        country: "United States",  region: "North America", lat: 47.4502, lng: -122.3088, timezone: "America/Los_Angeles" },
  { code: "YYZ", name: "Toronto Pearson",                city: "Toronto",        country: "Canada",         region: "North America", lat: 43.6777, lng: -79.6248, timezone: "America/Toronto" },
  { code: "LHR", name: "London Heathrow",                city: "London",         country: "United Kingdom", region: "Europe", lat: 51.4700, lng: -0.4543, timezone: "Europe/London" },
  { code: "CDG", name: "Paris Charles de Gaulle",        city: "Paris",          country: "France",         region: "Europe", lat: 49.0097, lng: 2.5479, timezone: "Europe/Paris" },
  { code: "FRA", name: "Frankfurt am Main",              city: "Frankfurt",      country: "Germany",        region: "Europe", lat: 50.0379, lng: 8.5622, timezone: "Europe/Berlin" },
  { code: "AMS", name: "Amsterdam Schiphol",              city: "Amsterdam",      country: "Netherlands",    region: "Europe", lat: 52.3105, lng: 4.7683, timezone: "Europe/Amsterdam" },
  { code: "MAD", name: "Adolfo Suárez Madrid-Barajas",    city: "Madrid",         country: "Spain",          region: "Europe", lat: 40.4983, lng: -3.5676, timezone: "Europe/Madrid" },
  { code: "DXB", name: "Dubai International",             city: "Dubai",          country: "United Arab Emirates", region: "Middle East", lat: 25.2532, lng: 55.3657, timezone: "Asia/Dubai" },
  { code: "IST", name: "Istanbul Airport",                city: "Istanbul",       country: "Turkey",         region: "Europe", lat: 41.2753, lng: 28.7519, timezone: "Europe/Istanbul" },
  { code: "SIN", name: "Singapore Changi",                city: "Singapore",      country: "Singapore",      region: "Asia", lat: 1.3644, lng: 103.9915, timezone: "Asia/Singapore" },
  { code: "HKG", name: "Hong Kong International",         city: "Hong Kong",       country: "China",          region: "Asia", lat: 22.3080, lng: 113.9185, timezone: "Asia/Hong_Kong" },
  { code: "NRT", name: "Tokyo Narita",                    city: "Tokyo",          country: "Japan",          region: "Asia", lat: 35.7720, lng: 140.3929, timezone: "Asia/Tokyo" },
  { code: "ICN", name: "Seoul Incheon",                   city: "Seoul",          country: "South Korea",    region: "Asia", lat: 37.4602, lng: 126.4407, timezone: "Asia/Seoul" },
  { code: "BOM", name: "Chhatrapati Shivaji Maharaj",     city: "Mumbai",          country: "India",          region: "Asia", lat: 19.0896, lng: 72.8656, timezone: "Asia/Kolkata" },
  { code: "KHI", name: "Jinnah International",             city: "Karachi",        country: "Pakistan",       region: "Asia", lat: 24.9008, lng: 67.1681, timezone: "Asia/Karachi" },
  { code: "SYD", name: "Sydney Kingsford Smith",          city: "Sydney",         country: "Australia",      region: "Oceania", lat: -33.9399, lng: 151.1753, timezone: "Australia/Sydney" },
];

// Popular route pairs to seed flights for.
const ROUTES: [string, string][] = [
  ["JFK", "LHR"], ["LHR", "JFK"],
  ["JFK", "LAX"], ["LAX", "JFK"],
  ["SFO", "NRT"], ["NRT", "SFO"],
  ["LAX", "SYD"], ["SYD", "LAX"],
  ["DXB", "LHR"], ["LHR", "DXB"],
  ["CDG", "JFK"], ["JFK", "CDG"],
  ["SIN", "HKG"], ["HKG", "SIN"],
  ["FRA", "ORD"], ["ORD", "FRA"],
  ["DXB", "KHI"], ["KHI", "DXB"],
  ["AMS", "JFK"], ["JFK", "AMS"],
  ["BOM", "DXB"], ["DXB", "BOM"],
  ["SEA", "ICN"], ["ICN", "SEA"],
  ["MIA", "MAD"], ["MAD", "MIA"],
  ["IST", "FRA"], ["FRA", "IST"],
  ["YYZ", "LHR"], ["LHR", "YYZ"],
];

// Haversine distance in km
function distanceKm(a: AirportSeed, b: AirportSeed) {
  const R = 6371;
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLng = ((b.lng - a.lng) * Math.PI) / 180;
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((a.lat * Math.PI) / 180) *
      Math.cos((b.lat * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return Math.round(2 * R * Math.asin(Math.sqrt(s)));
}

function durationMin(km: number) {
  return Math.round((km / 850) * 60) + 25;
}

function aircraftFor(km: number) {
  if (km < 1500) return { code: "ERJ-190", seats: 24 };
  if (km < 4000) return { code: "A320neo", seats: 150 };
  if (km < 9000) return { code: "787-9", seats: 216 };
  return { code: "A350-900", seats: 254 };
}

const CABIN_MULT = { economy: 1.0, business: 2.6, first: 4.2 } as const;

function basePrice(km: number) {
  return Math.round((km * 0.09 + 90) * 100) / 100;
}

function pad(n: number) {
  return n.toString().padStart(2, "0");
}

function dateOffset(days: number, hour: number, minute: number) {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + days);
  d.setUTCHours(hour, minute, 0, 0);
  return d;
}

async function main() {
  console.log("Clearing existing data…");
  await db.booking.deleteMany();
  await db.seat.deleteMany();
  await db.flight.deleteMany();
  await db.airport.deleteMany();

  console.log(`Seeding ${AIRPORTS.length} airports…`);
  for (const a of AIRPORTS) {
    await db.airport.create({ data: a });
  }

  console.log(`Seeding flights for ${ROUTES.length} routes over the next 14 days…`);
  let flightCounter = 0;

  for (const [fromCode, toCode] of ROUTES) {
    const from = AIRPORTS.find((a) => a.code === fromCode)!;
    const to = AIRPORTS.find((a) => a.code === toCode)!;
    const km = distanceKm(from, to);
    const durMin = durationMin(km);
    const ac = aircraftFor(km);
    const price = basePrice(km);

    for (let day = 1; day <= 14; day++) {
      const departuresPerDay = day % 3 === 0 ? 2 : 1;
      for (let k = 0; k < departuresPerDay; k++) {
        const hour = 6 + k * 8 + ((fromCode.charCodeAt(0) + day) % 6);
        const minute = (fromCode.charCodeAt(1) * 7 + day) % 60;
        const dep = dateOffset(day, hour % 23, minute);
        const arr = new Date(dep.getTime() + durMin * 60_000);

        flightCounter++;
        const flightNumber = `SKY-${(200 + flightCounter).toString()}`;
        const total = ac.seats;

        const flight = await db.flight.create({
          data: {
            flightNumber,
            airline: "Skyway Air",
            airlineCode: "SKY",
            fromCode,
            toCode,
            departureTime: dep,
            arrivalTime: arr,
            durationMin: durMin,
            aircraft: ac.code,
            totalSeats: total,
            availableSeats: total,
            priceEconomy: price,
            priceBusiness: Math.round(price * CABIN_MULT.business * 100) / 100,
            priceFirst: Math.round(price * CABIN_MULT.first * 100) / 100,
            status: "scheduled",
            gate: `T${(day % 9) + 1}-${pad((k * 13) % 30 + 1)}`,
          },
        });

        // Generate seats (6-abreast A-B-C-D-E-F)
        const rows = Math.ceil(total / 6);
        const cols = ["A", "B", "C", "D", "E", "F"];
        const seatsData: any[] = [];
        for (let r = 1; r <= rows; r++) {
          for (let c = 0; c < cols.length; c++) {
            if ((r - 1) * 6 + c + 1 > total) break;
            const cabin = r <= 2 ? "first" : r <= 6 ? "business" : "economy";
            const mult = CABIN_MULT[cabin as keyof typeof CABIN_MULT];
            seatsData.push({
              flightId: flight.id,
              seatNumber: `${r}${cols[c]}`,
              cabinClass: cabin,
              row: r,
              column: cols[c],
              isAvailable: true,
              price: Math.round(price * mult * 100) / 100,
            });
          }
        }
        await db.seat.createMany({ data: seatsData });
      }
    }
  }

  console.log(`✓ Seeded ${flightCounter} flights.`);
  console.log("Seed complete.");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await db.$disconnect();
  });
