import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export const dynamic = "force-dynamic";

// GET /api/booking/[id] — fetch a booking by its reference (passed as id) or row id.
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  // Try by reference first, fall back to row id.
  let booking = await db.booking.findUnique({
    where: { reference: id },
    include: { flight: { include: { fromAirport: true, toAirport: true } } },
  });

  if (!booking) {
    booking = await db.booking.findUnique({
      where: { id },
      include: { flight: { include: { fromAirport: true, toAirport: true } } },
    });
  }

  if (!booking) {
    return NextResponse.json({ error: "Booking not found" }, { status: 404 });
  }

  return NextResponse.json({ booking });
}
