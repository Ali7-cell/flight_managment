import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export const dynamic = "force-dynamic";

// GET /api/flights/[id]/seats
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  const flight = await db.flight.findUnique({
    where: { id },
    include: { fromAirport: true, toAirport: true },
  });
  if (!flight) {
    return NextResponse.json({ error: "Flight not found" }, { status: 404 });
  }

  const seats = await db.seat.findMany({
    where: { flightId: id },
    orderBy: [{ row: "asc" }, { column: "asc" }],
  });

  return NextResponse.json({ flight, seats });
}
