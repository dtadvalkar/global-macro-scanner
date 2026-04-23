import requests
import asyncio
from config import TELEGRAM

_EXCHANGE_INFO = {
    '.NS': ('🇮🇳', '₹',    'NSE'),
    '.BO': ('🇮🇳', '₹',    'BSE'),
    '.AX': ('🇦🇺', 'A$',   'ASX'),
    '.SI': ('🇸🇬', 'S$',   'SGX'),
    '.HK': ('🇭🇰', 'HK$',  'SEHK'),
    '.L':  ('🇬🇧', '£',    'LSE'),
    '.JO': ('🇿🇦', 'R',    'JSE'),
    '.SR': ('🇸🇦', 'SAR ', 'TADAWUL'),
    '.T':  ('🇯🇵', '¥',    'TSE'),
    '.TO': ('🇨🇦', 'CA$',  'TSX'),
    '.DE': ('🇩🇪', '€',    'XETRA'),
    '.PA': ('🇫🇷', '€',    'Euronext'),
    '.KS': ('🇰🇷', '₩',    'KRX'),
    '.TW': ('🇹🇼', 'NT$',  'TWSE'),
    '.SA': ('🇧🇷', 'R$',   'Bovespa'),
    '.KL': ('🇲🇾', 'RM ',  'Bursa'),
    '.BK': ('🇹🇭', '฿',    'SET'),
    '.JK': ('🇮🇩', 'Rp ',  'IDX'),
}

def _exchange_info(symbol: str):
    for suffix, info in _EXCHANGE_INFO.items():
        if symbol.endswith(suffix):
            return info
    return ('🌐', '$', 'US/OTHER')


def _signal_strength(catch: dict):
    rsi = catch.get('rsi')
    rvol = catch.get('rvol', 0)
    if rsi is not None and rsi <= 25 and rvol >= 5.0:
        return '🔥', 'EXTREME'
    if (rsi is not None and rsi <= 35) or rvol >= 3.0:
        return '⚡', 'STRONG'
    return '📌', 'WATCH'


def _format_stock_line(catch: dict) -> str:
    symbol = catch.get('symbol', catch.get('ticker', 'UNKNOWN'))
    price = catch.get('price', 0)
    pct_from_low = catch.get('pct_from_low', 0)
    rvol = catch.get('rvol', 0)
    rsi = catch.get('rsi')
    atr = catch.get('atr_pct')

    _, currency, _ = _exchange_info(symbol)
    strength_icon, _ = _signal_strength(catch)

    parts = [f"{strength_icon} `{symbol}` — {currency}{price:,.2f} | +{pct_from_low:.1%}"]
    if rsi is not None:
        parts.append(f"RSI {rsi:.0f}")
    if rvol:
        parts.append(f"RVOL {rvol:.1f}x")
    if atr:
        parts.append(f"ATR {atr:.1%}")

    return " | ".join(parts)


def _format_batch_message(catches: list) -> str:
    total = len(catches)
    groups: dict = {}
    for catch in catches:
        symbol = catch.get('symbol', catch.get('ticker', ''))
        flag, _, exchange = _exchange_info(symbol)
        groups.setdefault((flag, exchange), []).append(catch)

    lines = [f"📊 *DAILY SCAN — {total} SIGNAL{'S' if total > 1 else ''}*\n"]
    for (flag, exchange), group in sorted(groups.items(), key=lambda x: x[0][1]):
        lines.append(f"{flag} *{exchange} ({len(group)})*")
        for catch in group:
            lines.append(_format_stock_line(catch))
        lines.append("")

    return "\n".join(lines).strip()


async def _post_with_retry(url: str, payload: dict, max_attempts: int = 3) -> bool:
    for attempt in range(1, max_attempts + 1):
        try:
            response = await asyncio.to_thread(requests.post, url, json=payload, timeout=10)
            if response.status_code == 200:
                return True
            if response.status_code == 429:
                wait = 2 ** attempt
                print(f"⚠️  Telegram rate limited — retrying in {wait}s (attempt {attempt}/{max_attempts})")
                await asyncio.sleep(wait)
            else:
                print(f"❌ Telegram API error ({response.status_code}): {response.text[:120]}")
                return False
        except Exception as e:
            if attempt < max_attempts:
                wait = 2 ** attempt
                print(f"⚠️  Telegram error: {e} — retrying in {wait}s ({attempt}/{max_attempts})")
                await asyncio.sleep(wait)
            else:
                print(f"❌ Telegram failed after {max_attempts} attempts: {e}")
                return False
    return False


async def send_alerts(catches):
    """Send all catches as one batched message grouped by exchange."""
    if not catches:
        return

    if not TELEGRAM['token'] or not TELEGRAM['chat_id']:
        print("⚠️  Telegram not configured (TOKEN or CHAT_ID missing). Skipping alerts.")
        return

    print(f"🔔 Sending Telegram alert ({len(catches)} signal{'s' if len(catches) > 1 else ''})...")
    url = f"https://api.telegram.org/bot{TELEGRAM['token']}/sendMessage"
    payload = {
        'chat_id': TELEGRAM['chat_id'],
        'text': _format_batch_message(catches),
        'parse_mode': 'Markdown',
    }
    if await _post_with_retry(url, payload):
        print(f"✅ Telegram alert sent ({len(catches)} signals).")


async def send_alert(catch):
    """Send a single-stock alert. Kept for backward compatibility."""
    await send_alerts([catch])
