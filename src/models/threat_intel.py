from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ThreatIndicator


class ThreatIntelRegistry:
    """
    Registry for blacklisted financial risk vectors.
    Performs real-time lookups on IP, device, account, and merchant indicators.
    """

    @staticmethod
    async def evaluate_transaction(db: AsyncSession, tx_payload: dict) -> dict:
        """
        Cross-references transaction parameters against the threat database.
        Returns match status, matched indicators, and cumulative risk multiplier.
        """
        matched_indicators = []
        cumulative_multiplier = 1.0

        # Extract values
        checks = [
            ("IP", tx_payload.get("ip_address")),
            ("DEVICE", tx_payload.get("device_id")),
            ("ACCOUNT", tx_payload.get("sender_id")),
            ("MERCHANT", tx_payload.get("receiver_id")),
            ("MERCHANT", tx_payload.get("merchant_category")),  # check category as well
        ]

        # Filter out empty checks
        valid_checks = [(t, v) for t, v in checks if v]
        if not valid_checks:
            return {"matched": False, "indicators": [], "risk_multiplier": 1.0}

        # Build values list for SQL IN query
        values = [v for _, v in valid_checks]

        stmt = select(ThreatIndicator).where(ThreatIndicator.value.in_(values))
        res = await db.execute(stmt)
        matched_rows = res.scalars().all()

        if matched_rows:
            for row in matched_rows:
                matched_indicators.append(
                    {
                        "type": row.indicator_type,
                        "value": row.value,
                        "risk_multiplier": row.risk_multiplier,
                        "source": row.source,
                    }
                )
                # Multiply risk multipliers
                cumulative_multiplier *= row.risk_multiplier

            return {
                "matched": True,
                "indicators": matched_indicators,
                "risk_multiplier": round(cumulative_multiplier, 3),
            }

        return {"matched": False, "indicators": [], "risk_multiplier": 1.0}
