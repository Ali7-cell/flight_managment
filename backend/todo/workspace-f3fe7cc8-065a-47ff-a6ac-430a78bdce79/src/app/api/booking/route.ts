import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export const dynamic = "force-dynamic";

function refCode() {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let s = "SKY-";
  for (let i = 0; i < 5; i++) s += chars[Math.floor(Math.random() * chars.length)];
  return s;
}

// POST /api/booking
// Body: { flightId, seatNumber, cabinClass, passengerName, passengerEmail, passengerPhone?, paymentMethod? }
export async function POST(req: NextRequest) {
  let body: any;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { flightId, seatNumber, cabinClass, passengerName, passengerEmail, passengerPhone, paymentMethod } = body;
  if (!flightId || !seatNumber || !cabinClass || !passengerName || !passengerEmail) {
    return NextResponse.json(
      { error: "Missing required fields: flightId, seatNumber, cabinClass, passengerName, passengerEmail" },
      { status: 400 }
    );
  }

  // Validate flight
  const flight = await db.flight.findUnique({ where: { id: flightId } });
  if (!flight) return NextResponse.json({ error: "Flight not found" }, { status: 404 });

  // Validate seat belongs to flight & is available
  const seat = await db.seat.findUnique({
    where: { flightId_seatNumber: { flightId, seatNumber } },
  });
  if (!seat) return NextResponse.json({ error: "Seat not found" }, { status: 404 });
  if (!seat.isAvailable)
    return NextResponse.json({ error: "Seat is already booked" }, { status: 409 });

  // Calculate total
  const priceMap = { economy: flight.priceEconomy, business: flight.priceBusiness, first: flight.priceFirst } as const;
  const basePrice = priceMap[cabinClass as keyof typeof priceMap] ?? flight.priceEconomy;
  // Use the seat-specific price (which is already computed per cabin) when available
  const total = seat.price ?? basePrice;

  // Create booking + mark seat unavailable (transaction)
  let reference = refCode();
  // Ensure reference is unique (try a few times)
  let attempts = 0;
  while (attempts < 5) {
    const existing = await db.booking.findUnique({ where: { reference } });
    if (!existing) break;
    reference = refCode();
    attempts++;
  }

  const booking = await db.$transaction(async (tx) => {
    const b = await tx.booking.create({
      data: {
        reference,
        flightId,
        seatNumber,
        cabinClass,
        passengerName,
        passengerEmail,
        passengerPhone: passengerPhone || null,
        totalAmount: total,
        currency: "USD",
        status: "confirmed",
        paymentMethod: paymentMethod || "card",
        paymentStatus: "paid",
      },
    });
    await tx.seat.update({
      where: { id: seat.id },
      data: { isAvailable: false },
    });
    await tx.flight.update({
      where: { id: flightId },
      data: { availableSeats: { decrement: 1 } },
    });
    return b;
  });

  return NextResponse.json({ booking }, { status: 201 });
}
