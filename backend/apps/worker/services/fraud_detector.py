from typing import Any

def score_booking(booking: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """
    Evaluates booking characteristics to flag mass-booking or bot fraud patterns.
    Returns (score 0..1, signals dictionary).
    """
    signals = {}
    score = 0.0

    # Signal 1: Group velocity (booking 9 seats in one go)
    qty = booking.get("quantity", 1)
    if qty >= 8:
        signals["bulk_quantity"] = True
        score += 0.4
    else:
        signals["bulk_quantity"] = False

    # Signal 2: High total amount outlier
    amount = float(booking.get("total_amount", 0.0))
    if amount > 5000.0:
        signals["high_value_transaction"] = True
        score += 0.3
    else:
        signals["high_value_transaction"] = False

    # Signal 3: Repetitive passenger patterns (stub)
    signals["velocity_frequency"] = "normal"

    final_score = min(1.0, round(score, 2))
    return final_score, signals
