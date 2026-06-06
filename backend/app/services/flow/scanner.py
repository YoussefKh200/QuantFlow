"""
Options Flow Scanner.

Classifies inbound option trades by:
  - Type: sweep, block, split
  - Sentiment: bullish, bearish, neutral
  - Significance: unusual (relative to OI), institutional (size)
  - Flow score: composite 0–1 conviction metric

A "sweep" is an aggressive market-order that sweeps multiple exchanges
simultaneously — strong directional intent.  Blocks are large single
prints, often opening new positions.

Scoring methodology:
  Premium rank  — premium_total relative to 30-day median for this strike
  Size rank     — trade_size relative to open_interest
  Aggressiveness — BUY at ask vs SELL at bid (paid vs received)
  IV differential — bid/ask IV spread (wider = more conviction on direction)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FlowEvent:
    """A single classified options trade."""
    contract_id: str
    underlying: str
    strike: float
    expiration: date
    option_type: str         # 'C' or 'P'
    trade_size: int
    trade_price: float
    trade_side: str          # 'BUY' or 'SELL'
    aggressor: str           # 'BUYER' or 'SELLER'
    trade_type: str          # 'sweep', 'block', 'split'
    premium_total: float     # size * price * 100
    sentiment: str           # 'bullish', 'bearish', 'neutral'
    is_unusual: bool
    is_institutional: bool
    flow_score: float        # 0–1
    exchange: str
    open_interest: int
    timestamp: datetime


class FlowScanner:
    """
    Classifies raw tape prints into structured flow events.

    Thresholds (calibrated for US equity options market):
      BLOCK_SIZE          — ≥ 250 contracts
      SWEEP_EXCHANGES     — ≥ 3 exchanges filled simultaneously
      UNUSUAL_OI_RATIO    — trade size ≥ 5% of open interest
      INSTITUTIONAL_SIZE  — ≥ 500 contracts OR premium ≥ $500k
    """

    BLOCK_SIZE = 250
    UNUSUAL_OI_RATIO = 0.05       # 5% of OI
    INSTITUTIONAL_MIN_SIZE = 500
    INSTITUTIONAL_MIN_PREMIUM = 500_000    # $500k

    def classify_trade(
        self,
        contract_id: str,
        underlying: str,
        strike: float,
        expiration: date,
        option_type: str,
        trade_size: int,
        trade_price: float,
        bid: float,
        ask: float,
        open_interest: int,
        exchange_count: int,          # how many exchanges filled simultaneously
        timestamp: datetime,
        exchange: str = "UNKNOWN",
    ) -> FlowEvent:
        """
        Classify a single tape print into a FlowEvent.

        Exchange count > 1 signals a sweep (aggressive market order
        routing across multiple venues simultaneously).
        """
        premium_total = trade_size * trade_price * 100.0

        # --- Trade type classification ---
        if exchange_count >= 3:
            trade_type = "sweep"
        elif trade_size >= self.BLOCK_SIZE:
            trade_type = "block"
        else:
            trade_type = "split"

        # --- Aggressor direction (paid vs received) ---
        mid = (bid + ask) / 2.0
        if trade_price >= ask * 0.98:
            aggressor = "BUYER"     # paid at/near ask — aggressive buyer
            trade_side = "BUY"
        elif trade_price <= bid * 1.02:
            aggressor = "SELLER"    # sold at/near bid — aggressive seller
            trade_side = "SELL"
        else:
            aggressor = "BUYER" if trade_price > mid else "SELLER"
            trade_side = "BUY" if aggressor == "BUYER" else "SELL"

        # --- Sentiment ---
        sentiment = self._classify_sentiment(option_type, trade_side, aggressor)

        # --- Unusual flag ---
        is_unusual = (
            (open_interest > 0 and trade_size / open_interest >= self.UNUSUAL_OI_RATIO)
            or trade_type == "sweep"
            or (trade_size >= self.BLOCK_SIZE and premium_total >= 250_000)
        )

        # --- Institutional flag ---
        is_institutional = (
            trade_size >= self.INSTITUTIONAL_MIN_SIZE
            or premium_total >= self.INSTITUTIONAL_MIN_PREMIUM
        )

        # --- Flow score (0–1 conviction) ---
        flow_score = self._compute_flow_score(
            trade_size=trade_size,
            premium_total=premium_total,
            open_interest=open_interest,
            trade_type=trade_type,
            aggressor=aggressor,
            bid=bid,
            ask=ask,
            trade_price=trade_price,
        )

        return FlowEvent(
            contract_id=contract_id,
            underlying=underlying,
            strike=strike,
            expiration=expiration,
            option_type=option_type,
            trade_size=trade_size,
            trade_price=trade_price,
            trade_side=trade_side,
            aggressor=aggressor,
            trade_type=trade_type,
            premium_total=premium_total,
            sentiment=sentiment,
            is_unusual=is_unusual,
            is_institutional=is_institutional,
            flow_score=flow_score,
            exchange=exchange,
            open_interest=open_interest,
            timestamp=timestamp,
        )

    def _classify_sentiment(
        self, option_type: str, trade_side: str, aggressor: str
    ) -> str:
        """
        Sentiment matrix:

        |              | BUY (paid) | SELL (received) |
        |  Call        |  Bullish   |  Bearish        |
        |  Put         |  Bearish   |  Bullish        |

        Aggressor direction is the key signal.
        Seller of calls = bearish (capping upside).
        Buyer of puts = bearish (buying protection).
        """
        if aggressor == "BUYER":
            return "bullish" if option_type == "C" else "bearish"
        else:  # SELLER
            return "bearish" if option_type == "C" else "bullish"

    def _compute_flow_score(
        self,
        trade_size: int,
        premium_total: float,
        open_interest: int,
        trade_type: str,
        aggressor: str,
        bid: float,
        ask: float,
        trade_price: float,
    ) -> float:
        """
        Composite flow conviction score (0–1).

        Components:
          size_score      — log-normalized trade size (0.2 weight)
          premium_score   — log-normalized premium (0.3 weight)
          oi_score        — ratio of size to OI (0.2 weight)
          type_score      — sweep > block > split (0.2 weight)
          aggressiveness  — how close to ask/bid (0.1 weight)
        """
        import math

        # Size score: log scale 1–10000 contracts → 0–1
        size_score = min(math.log10(max(trade_size, 1)) / 4.0, 1.0)

        # Premium score: log scale $1k–$10M → 0–1
        premium_score = min(math.log10(max(premium_total, 1000)) / 7.0, 1.0)

        # OI ratio score
        oi_score = min(trade_size / max(open_interest, 1) / 0.10, 1.0) if open_interest > 0 else 0.3

        # Trade type score
        type_scores = {"sweep": 1.0, "block": 0.7, "split": 0.3}
        type_score = type_scores.get(trade_type, 0.3)

        # Aggressiveness: 1 = at ask, 0 = at mid
        spread = ask - bid
        if spread > 0:
            if aggressor == "BUYER":
                aggressiveness = min((trade_price - bid) / spread, 1.0)
            else:
                aggressiveness = min((ask - trade_price) / spread, 1.0)
        else:
            aggressiveness = 0.5

        score = (
            size_score * 0.20
            + premium_score * 0.30
            + oi_score * 0.20
            + type_score * 0.20
            + aggressiveness * 0.10
        )

        return round(min(max(score, 0.0), 1.0), 4)


class FlowSentimentAggregator:
    """
    Aggregates flow events into a symbol-level bull/bear sentiment score.

    Method: premium-weighted call/put ratio adjusted for aggressor direction.
    """

    def compute_sentiment(self, events: list[FlowEvent]) -> dict:
        """
        Returns a sentiment snapshot for a symbol.

        bull_premium  — total $ premium in bullish trades
        bear_premium  — total $ premium in bearish trades
        sentiment_score — -1 (max bear) to +1 (max bull)
        """
        if not events:
            return {
                "sentiment_score": 0.0,
                "bull_premium": 0.0,
                "bear_premium": 0.0,
                "neutral_premium": 0.0,
                "dominant": "neutral",
                "n_events": 0,
            }

        bull_premium = sum(e.premium_total for e in events if e.sentiment == "bullish")
        bear_premium = sum(e.premium_total for e in events if e.sentiment == "bearish")
        neutral_premium = sum(e.premium_total for e in events if e.sentiment == "neutral")
        total = bull_premium + bear_premium + neutral_premium

        if total == 0:
            score = 0.0
        else:
            score = (bull_premium - bear_premium) / total

        if score > 0.2:
            dominant = "bullish"
        elif score < -0.2:
            dominant = "bearish"
        else:
            dominant = "neutral"

        # Unusual-flow weighted score
        unusual_events = [e for e in events if e.is_unusual]
        if unusual_events:
            ub = sum(e.premium_total for e in unusual_events if e.sentiment == "bullish")
            ue = sum(e.premium_total for e in unusual_events if e.sentiment == "bearish")
            ut = ub + ue
            unusual_score = (ub - ue) / ut if ut > 0 else 0.0
        else:
            unusual_score = 0.0

        return {
            "sentiment_score": round(score, 4),
            "unusual_sentiment_score": round(unusual_score, 4),
            "bull_premium": round(bull_premium, 2),
            "bear_premium": round(bear_premium, 2),
            "neutral_premium": round(neutral_premium, 2),
            "total_premium": round(total, 2),
            "dominant": dominant,
            "n_events": len(events),
            "n_unusual": len(unusual_events),
            "n_institutional": sum(1 for e in events if e.is_institutional),
        }

    def top_unusual_flows(
        self,
        events: list[FlowEvent],
        n: int = 20,
        min_flow_score: float = 0.5,
    ) -> list[dict]:
        """Return top N unusual flow events sorted by premium."""
        unusual = [
            e for e in events
            if e.is_unusual and e.flow_score >= min_flow_score
        ]
        unusual.sort(key=lambda e: e.premium_total, reverse=True)
        return [
            {
                "underlying": e.underlying,
                "strike": e.strike,
                "expiration": str(e.expiration),
                "option_type": e.option_type,
                "trade_type": e.trade_type,
                "trade_size": e.trade_size,
                "premium_total": round(e.premium_total, 0),
                "sentiment": e.sentiment,
                "flow_score": e.flow_score,
                "is_institutional": e.is_institutional,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in unusual[:n]
        ]
