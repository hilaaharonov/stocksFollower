"""AI notes service using OpenAI."""

import logging
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)


def generate_ai_note(symbol: str, stock_info: dict, recent_prices: list[dict]) -> str:
    """Generate an AI analysis note for a stock symbol.

    Falls back to a rule-based note when OpenAI is not configured.
    """
    if settings.openai_api_key:
        return _generate_with_openai(symbol, stock_info, recent_prices)
    return _generate_basic_note(symbol, stock_info, recent_prices)


def _generate_with_openai(symbol: str, stock_info: dict, recent_prices: list[dict]) -> str:
    """Generate note using OpenAI chat completions."""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)

        prices_summary = ""
        if recent_prices:
            closes = [p["close"] for p in recent_prices if p.get("close") is not None]
            if closes:
                prices_summary = (
                    f"Recent closing prices (latest first): "
                    f"{', '.join(f'{c:.2f}' for c in closes[:10])}. "
                    f"30-day range: {min(closes):.2f} – {max(closes):.2f}."
                )

        prompt = (
            f"You are a financial analyst assistant. "
            f"Provide a brief, factual 3-sentence analysis note for the stock {symbol} "
            f"({stock_info.get('name', symbol)}). "
            f"Sector: {stock_info.get('sector', 'N/A')}. "
            f"{prices_summary} "
            f"Note: This is for informational purposes only, not financial advice."
        )

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("OpenAI API error for %s: %s", symbol, exc)
        return _generate_basic_note(symbol, stock_info, recent_prices)


def _generate_basic_note(symbol: str, stock_info: dict, recent_prices: list[dict]) -> str:
    """Generate a basic rule-based note without AI."""
    lines = [f"**{symbol}** – {stock_info.get('name', symbol)}"]

    if stock_info.get("sector"):
        lines.append(f"Sector: {stock_info['sector']}.")

    if recent_prices:
        closes = [p["close"] for p in recent_prices if p.get("close") is not None]
        if len(closes) >= 2:
            latest = closes[0]
            prev = closes[1]
            change_pct = (latest - prev) / prev * 100 if prev else 0
            direction = "▲" if change_pct >= 0 else "▼"
            lines.append(
                f"Latest close: ${latest:.2f} ({direction}{abs(change_pct):.2f}% vs previous)."
            )
        if len(closes) >= 5:
            trend_closes = closes[:5]
            if trend_closes[0] > trend_closes[-1]:
                trend = "upward"
            elif trend_closes[0] < trend_closes[-1]:
                trend = "downward"
            else:
                trend = "flat"
            lines.append(f"Recent 5-period trend: {trend}.")

    if not stock_info.get("sector") and len(recent_prices) < 2:
        lines.append("No recent price data available for analysis.")

    lines.append("⚠️ This note is for informational purposes only, not financial advice.")
    return " ".join(lines)
