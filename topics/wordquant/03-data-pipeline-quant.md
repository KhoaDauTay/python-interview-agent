# Module 03: Data Pipeline cho Quant Engineering — WorldQuant Interview Prep

> Mức độ: Medium → Hard | Phù hợp: Quant Engineering / Data Engineer roles tại WorldQuant

---

## Phần 1: Financial Data Types — Phải biết

---

### OHLCV Data (Open/High/Low/Close/Volume)

```
OHLCV là dữ liệu cơ bản nhất trong finance:
┌────────────┬────────┬────────┬────────┬────────┬───────────┐
│ Date       │ Open   │ High   │ Low    │ Close  │ Volume    │
├────────────┼────────┼────────┼────────┼────────┼───────────┤
│ 2024-01-02 │ 185.21 │ 188.44 │ 183.95 │ 187.15 │ 89,425,000│
│ 2024-01-03 │ 187.15 │ 189.22 │ 185.83 │ 186.19 │ 71,234,000│
└────────────┴────────┴────────┴────────┴────────┴───────────┘

- Open: giá mở cửa (first trade of session)
- High: giá cao nhất trong ngày
- Low: giá thấp nhất trong ngày
- Close: giá đóng cửa (last trade of session)
- Volume: tổng khối lượng giao dịch

Đặc điểm quan trọng:
- Adjusted Close: Close đã điều chỉnh theo corporate actions
- VWAP (Volume-Weighted Average Price): average price weighted by volume
- Granularity: daily, hourly, 1-min, tick
```

```python
import pandas as pd
import numpy as np
from dataclasses import dataclass

@dataclass
class OHLCVBar:
    symbol: str
    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: float | None = None

def validate_ohlcv(bar: OHLCVBar) -> list[str]:
    """Sanity checks cho OHLCV data."""
    errors = []
    if bar.high < bar.low:
        errors.append(f"High ({bar.high}) < Low ({bar.low})")
    if bar.open > bar.high or bar.open < bar.low:
        errors.append(f"Open ({bar.open}) outside [Low, High] range")
    if bar.close > bar.high or bar.close < bar.low:
        errors.append(f"Close ({bar.close}) outside [Low, High] range")
    if bar.volume < 0:
        errors.append(f"Negative volume: {bar.volume}")
    if bar.close <= 0:
        errors.append(f"Non-positive close price: {bar.close}")
    return errors
```

### Tick Data

```
Tick data = mỗi giao dịch riêng lẻ (finest granularity):
┌─────────────────────┬────────┬────────┬──────────┬──────┐
│ Timestamp           │ Price  │ Volume │ Exchange │ Side │
├─────────────────────┼────────┼────────┼──────────┼──────┤
│ 2024-01-02 09:30:00.001 │ 185.21 │ 100 │ NYSE │ Buy  │
│ 2024-01-02 09:30:00.005 │ 185.20 │ 500 │ ARCA │ Sell │
│ 2024-01-02 09:30:00.012 │ 185.22 │ 200 │ NYSE │ Buy  │
└─────────────────────┴────────┴────────┴──────────┴──────┘

Đặc điểm:
- Timestamp precision: microsecond hoặc nanosecond
- Volume: số cổ phiếu trong trade này (không phải ngày)
- US markets: ~1 tỷ ticks/ngày
- Size: ~100GB/ngày cho toàn bộ US equities
- Dùng cho: intraday analysis, HFT, market microstructure
```

### Order Book Data

```
Order book = trạng thái cung/cầu tại mỗi price level:

Level 2 Quote (Bid/Ask):
Bids (buyers)          │ Asks (sellers)
Price    Size  Orders  │ Price    Size  Orders
185.25   1,200   3    │ 185.30   2,500   5
185.24   3,500   8    │ 185.31   1,800   4
185.23   2,100   6    │ 185.32   5,000  12
185.22   4,800  15    │ 185.33   3,200   8
────────────────────────│────────────────────────
Spread = Ask - Bid = 185.30 - 185.25 = $0.05

Level 3 (Full book): mỗi individual order

Dùng cho: market microstructure research, execution quality analysis
Khó xử lý: cập nhật liên tục, size rất lớn
```

### Corporate Actions — Tại sao quan trọng cho Backtesting

```
Corporate actions thay đổi cấu trúc cổ phiếu → nếu không adjust, backtest sai!

1. Stock Split (e.g., 4:1 split):
   Trước: 1 cổ phiếu × $400
   Sau:   4 cổ phiếu × $100
   → Giá giảm 75%, nhưng không phải do mất tiền
   → Phải adjust historical prices ×0.25

2. Dividend:
   Ex-dividend date: giá giảm đúng bằng dividend amount
   → Nếu không adjust, thấy giá "drop" không có lý do
   → Dividend reinvestment giả định

3. Stock Merger/Acquisition:
   Company A mua Company B: giá B có thể nhảy lên 30%
   → Nếu backtest dùng giá không adjust, thấy "profit" ảo

4. Reverse Split (e.g., 1:10):
   Thường xảy ra khi cổ phiếu giá quá thấp
   → Adjust prices ×10 cho historical data
```

```python
import pandas as pd
import numpy as np

def adjust_prices_for_splits(
    prices: pd.Series,
    split_events: list[dict],
) -> pd.Series:
    """
    Adjust historical prices backward from today.
    split_events: [{"date": "2023-06-12", "ratio": 4.0}, ...]
    ratio = new_shares / old_shares (e.g., 4 for 4:1 split)
    """
    adjusted = prices.copy()
    for event in sorted(split_events, key=lambda x: x["date"], reverse=True):
        split_date = pd.Timestamp(event["date"])
        ratio = event["ratio"]
        # Adjust all prices BEFORE split date
        mask = adjusted.index < split_date
        adjusted[mask] = adjusted[mask] / ratio
    return adjusted

def adjust_prices_for_dividends(
    prices: pd.Series,
    dividends: pd.Series,  # dividend amount on each ex-date
    method: str = "ratio",
) -> pd.Series:
    """
    Adjust prices for dividends.
    method='ratio': multiply by (price - div) / price (recommended, no negative prices)
    """
    adjusted = prices.copy()
    for ex_date, div_amount in dividends.items():
        if div_amount > 0:
            price_on_date = prices.get(ex_date)
            if price_on_date and price_on_date > div_amount:
                ratio = (price_on_date - div_amount) / price_on_date
                mask = adjusted.index < ex_date
                adjusted[mask] *= ratio
    return adjusted
```

### Alternative Data

```
WorldQuant là leader trong alternative data research:

| Category          | Examples                              | Edge                      |
|-------------------|---------------------------------------|---------------------------|
| Sentiment         | News NLP, Twitter, Reddit             | Leading indicator         |
| Satellite         | Parking lot occupancy, oil tank fill  | Real-world activity       |
| Credit card       | Consumer spending by retailer         | Earnings surprise         |
| Web scraping      | Job postings, product prices          | Competitive intelligence  |
| Patent filings    | R&D activity, tech direction          | Innovation signal         |
| Shipping data     | AIS vessel tracking                   | Supply chain              |
| App download      | Mobile app rankings                   | Consumer behavior         |

Challenges:
- Point-in-time: data phải reflect what was KNOWN at that time
- Survivorship bias: defunct companies must be included
- Noise: alternative data often noisy, need heavy preprocessing
- Licensing: often expensive, restricted use
```

---

## Phần 2: Time-series Data Challenges

---

### Point-in-Time Correctness (Look-ahead Bias)

```
Look-ahead bias = backtest vô tình dùng thông tin từ TƯƠNG LAI.
Đây là sai lầm phổ biến nhất và nguy hiểm nhất trong backtesting.

EXAMPLE: Earnings data
- Company reports Q3 earnings on November 15
- But in database, record shows Q3 data starting from October 1
- If backtest trades on "Q3 data" on October 1 → LOOK-AHEAD BIAS!
- Correct: only use Q3 earnings AFTER November 15 release date

Timeline:
Oct 1 ─────────── Nov 15 ─────────── Feb 15
(Q3 period ends)  (Q3 earnings        (Q4 period ends)
                   released)

Point-in-time correct database stores:
- value_date: when the metric applies to (e.g., Sep 30 for Q3)
- release_date: when we ACTUALLY KNOW this info (e.g., Nov 15)
```

```python
import pandas as pd
from datetime import datetime, timedelta

class PointInTimeDatabase:
    """
    Correct implementation: each record has two dates.
    Query must specify AS_OF date — returns what was known at that time.
    """
    def __init__(self):
        # Each record: (symbol, value_date, release_date, value)
        self.records: list[dict] = []

    def insert(self, symbol: str, value_date: str, release_date: str, value: float):
        self.records.append({
            "symbol": symbol,
            "value_date": pd.Timestamp(value_date),
            "release_date": pd.Timestamp(release_date),
            "value": value,
        })

    def query_as_of(self, symbol: str, as_of_date: str) -> float | None:
        """
        Return the latest value that was KNOWN as of as_of_date.
        = the record with max(release_date) where release_date <= as_of_date.
        """
        as_of = pd.Timestamp(as_of_date)
        df = pd.DataFrame(self.records)
        mask = (
            (df["symbol"] == symbol) &
            (df["release_date"] <= as_of)  # only use what was known
        )
        available = df[mask]
        if available.empty:
            return None
        # Return most recently released value
        return float(available.loc[available["release_date"].idxmax(), "value"])

# Ví dụ
db = PointInTimeDatabase()
db.insert("AAPL", "2023-09-30", "2023-11-02", 1.46)  # Q3 EPS, released Nov 2
db.insert("AAPL", "2023-12-31", "2024-02-01", 2.18)  # Q4 EPS, released Feb 1

# Backtest trên Oct 15, 2023: chỉ thấy Q2 data (Q3 not yet released)
eps_oct = db.query_as_of("AAPL", "2023-10-15")  # None! Q3 not released yet

# Backtest trên Dec 1, 2023: thấy Q3 data
eps_dec = db.query_as_of("AAPL", "2023-12-01")  # 1.46 (Q3 EPS, released Nov 2)

print(f"Oct 15: {eps_oct}")  # None — correct!
print(f"Dec 1:  {eps_dec}")  # 1.46 — correct!
```

### Survivorship Bias

```
Survivorship bias: nếu backtest chỉ dùng cổ phiếu ĐANG TỒN TẠI hiện tại,
bạn vô tình chỉ bao gồm "survivors" — bỏ qua công ty đã phá sản/bị mua.

Example:
- S&P 500 năm 2000: bao gồm nhiều dot-com companies (Enron, WorldCom, ...)
- S&P 500 năm 2024: những công ty đó đã bị loại (vì phá sản)
- Nếu backtest S&P 500 "as of today" starting from 2000:
  - Bạn bỏ qua các công ty đã sập → results quá optimistic!

Fix: dùng "point-in-time universe" — thành phần của index TẠI THỜI ĐIỂM ĐÓ.
```

```python
class UniverseDatabase:
    """Track index constituents over time."""

    def __init__(self):
        # {symbol: [(add_date, remove_date), ...]}
        self.constituents: dict[str, list[tuple]] = {}

    def add_constituent(self, symbol: str, add_date: str, remove_date: str | None = None):
        if symbol not in self.constituents:
            self.constituents[symbol] = []
        self.constituents[symbol].append((
            pd.Timestamp(add_date),
            pd.Timestamp(remove_date) if remove_date else None,
        ))

    def get_universe_as_of(self, as_of_date: str) -> set[str]:
        """Return set of symbols that were IN the index on as_of_date."""
        as_of = pd.Timestamp(as_of_date)
        universe = set()
        for symbol, periods in self.constituents.items():
            for add_date, remove_date in periods:
                if add_date <= as_of:
                    if remove_date is None or remove_date > as_of:
                        universe.add(symbol)
        return universe

# Ví dụ
universe_db = UniverseDatabase()
universe_db.add_constituent("AAPL", "1980-01-01")               # still in
universe_db.add_constituent("ENRN", "1999-01-01", "2001-12-03") # Enron (bankrupt 2001)
universe_db.add_constituent("GOOG", "2004-08-19")               # still in

universe_2000 = universe_db.get_universe_as_of("2000-06-01")
universe_2024 = universe_db.get_universe_as_of("2024-01-01")

print(f"Universe 2000: {universe_2000}")  # includes ENRN
print(f"Universe 2024: {universe_2024}")  # excludes ENRN
```

### Data Gaps và Missing Values

```python
import pandas as pd
import numpy as np

def handle_missing_prices(
    prices: pd.DataFrame,  # index=dates, columns=symbols
    method: str = "ffill",
    max_gap_days: int = 5,
) -> pd.DataFrame:
    """
    Handle missing values in price data.

    Strategies:
    - ffill: forward-fill (assume last known price)
    - drop: drop stocks with too many gaps
    - interpolate: linear interpolation (use carefully — look-ahead on future prices!)
    """
    # Identify gaps
    missing_pct = prices.isnull().mean()
    bad_stocks = missing_pct[missing_pct > 0.1].index  # >10% missing
    print(f"Dropping {len(bad_stocks)} stocks with >10% missing: {list(bad_stocks)}")
    prices = prices.drop(columns=bad_stocks)

    # Forward fill (safe — only uses past data)
    if method == "ffill":
        prices = prices.ffill(limit=max_gap_days)
        # After ffill limit, remaining NaN = stock wasn't trading (correct)

    # Flag large gaps (possible data issue vs. holiday)
    gaps = prices.isnull().sum()
    suspicious = gaps[gaps > max_gap_days]
    if not suspicious.empty:
        print(f"Warning: stocks with large gaps: {suspicious.to_dict()}")

    return prices

def align_timezone(
    df: pd.DataFrame,
    source_tz: str,
    target_tz: str = "UTC",
) -> pd.DataFrame:
    """Convert timestamps to UTC for cross-market alignment."""
    df = df.copy()
    if df.index.tz is None:
        df.index = df.index.tz_localize(source_tz)
    df.index = df.index.tz_convert(target_tz)
    return df
```

---

## Phần 3: ETL Pipeline Design cho Market Data

---

### Architecture Overview

```
                        ETL Pipeline cho Market Data
                        ═══════════════════════════

┌─────────────────────────────────────────────────────────────────┐
│                         EXTRACT                                  │
│                                                                  │
│  ┌───────────┐  ┌───────────┐  ┌──────────┐  ┌─────────────┐   │
│  │ REST API  │  │ WebSocket │  │   FTP    │  │  S3/GCS     │   │
│  │ (daily)   │  │ (RT feed) │  │ (EOD)    │  │  (bulk)     │   │
│  └─────┬─────┘  └─────┬─────┘  └────┬─────┘  └──────┬──────┘   │
│        └──────────────┴─────────────┴────────────────┘          │
│                              │                                   │
└──────────────────────────────┼──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         TRANSFORM                                │
│                                                                  │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
│  │ Normalization  │  │ Corp. Action    │  │ Timezone         │  │
│  │ - schema valid │  │ Adjustment      │  │ Conversion       │  │
│  │ - type coerce  │  │ - splits        │  │ - local → UTC    │  │
│  │ - dedup        │  │ - dividends     │  │ - market hours   │  │
│  └────────────────┘  └─────────────────┘  └──────────────────┘  │
│                                                                  │
│  ┌────────────────┐  ┌─────────────────┐                        │
│  │ Quality Checks │  │ Enrichment      │                        │
│  │ - price spikes │  │ - VWAP calc     │                        │
│  │ - vol anomaly  │  │ - returns       │                        │
│  └────────────────┘  └─────────────────┘                        │
│                                                                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                           LOAD                                   │
│                                                                  │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
│  │  ClickHouse    │  │  Parquet/S3     │  │  Redis           │  │
│  │  (OLAP, fast   │  │  (archival,     │  │  (real-time      │  │
│  │   aggregation) │  │   batch jobs)   │  │   price cache)   │  │
│  └────────────────┘  └─────────────────┘  └──────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Extract — API Connectors và WebSocket Feeds

```python
import asyncio
import aiohttp
import websockets
import json
import logging
from datetime import datetime, date
from typing import AsyncIterator

logger = logging.getLogger(__name__)

class MarketDataExtractor:
    """Extract data từ nhiều sources."""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=aiohttp.ClientTimeout(total=30),
        )
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()

    async def fetch_ohlcv(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Fetch daily OHLCV with retry."""
        url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}"
        params = {"adjusted": "true", "sort": "asc", "limit": 50_000}

        for attempt in range(3):
            try:
                async with self._session.get(url, params=params) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    return data.get("results", [])
            except aiohttp.ClientError as e:
                if attempt == 2:
                    raise
                wait = 2 ** attempt
                logger.warning(f"Retry {attempt+1} for {symbol}: {e}. Wait {wait}s")
                await asyncio.sleep(wait)
        return []

    async def fetch_universe_parallel(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date,
        max_concurrent: int = 20,
    ) -> dict[str, list[dict]]:
        """Fetch all symbols concurrently with rate limiting."""
        semaphore = asyncio.Semaphore(max_concurrent)
        results: dict[str, list[dict]] = {}

        async def fetch_one(symbol: str):
            async with semaphore:
                try:
                    data = await self.fetch_ohlcv(symbol, start_date, end_date)
                    results[symbol] = data
                except Exception as e:
                    logger.error(f"Failed {symbol}: {e}")
                    results[symbol] = []

        await asyncio.gather(*[fetch_one(sym) for sym in symbols])
        return results


class RealtimeMarketDataStream:
    """WebSocket streaming for real-time data."""

    def __init__(self, ws_url: str, api_key: str):
        self.ws_url = ws_url
        self.api_key = api_key

    async def subscribe(self, symbols: list[str]) -> AsyncIterator[dict]:
        """Stream real-time ticks via WebSocket."""
        async with websockets.connect(self.ws_url) as ws:
            # Authenticate
            await ws.send(json.dumps({"action": "auth", "params": self.api_key}))
            auth_response = json.loads(await ws.recv())
            logger.info(f"Auth: {auth_response}")

            # Subscribe to symbols
            await ws.send(json.dumps({
                "action": "subscribe",
                "params": ",".join(f"T.{sym}" for sym in symbols),  # T.= trades
            }))

            # Stream ticks
            async for message in ws:
                ticks = json.loads(message)
                for tick in ticks:
                    if tick.get("ev") == "T":  # Trade event
                        yield {
                            "symbol": tick["sym"],
                            "price": tick["p"],
                            "volume": tick["s"],
                            "timestamp": pd.Timestamp(tick["t"], unit="ms", tz="UTC"),
                            "exchange": tick.get("x"),
                        }
```

### Transform — Normalization và Validation

```python
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional

class OHLCVRecord(BaseModel):
    """Schema validation với Pydantic."""
    symbol: str
    date: pd.Timestamp
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)
    adj_close: Optional[float] = None
    vwap: Optional[float] = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        v = v.upper().strip()
        if not v.isalpha() or len(v) > 10:
            raise ValueError(f"Invalid symbol: {v}")
        return v

    @model_validator(mode="after")
    def validate_ohlc_consistency(self) -> "OHLCVRecord":
        if self.high < self.low:
            raise ValueError(f"High {self.high} < Low {self.low}")
        if not (self.low <= self.open <= self.high):
            raise ValueError(f"Open {self.open} outside [Low={self.low}, High={self.high}]")
        if not (self.low <= self.close <= self.high):
            raise ValueError(f"Close {self.close} outside [Low={self.low}, High={self.high}]")
        return self

    class Config:
        arbitrary_types_allowed = True


def normalize_raw_data(raw_records: list[dict], symbol: str) -> pd.DataFrame:
    """Normalize raw API response to standard schema."""
    validated = []
    errors = []

    for record in raw_records:
        try:
            ohlcv = OHLCVRecord(
                symbol=symbol,
                date=pd.Timestamp(record["t"], unit="ms", tz="UTC").normalize(),
                open=record["o"],
                high=record["h"],
                low=record["l"],
                close=record["c"],
                volume=record["v"],
                vwap=record.get("vw"),
                adj_close=record.get("c"),  # use close as adj_close initially
            )
            validated.append(ohlcv.model_dump())
        except Exception as e:
            errors.append({"record": record, "error": str(e)})

    if errors:
        logger.warning(f"Validation errors for {symbol}: {len(errors)}/{len(raw_records)}")

    return pd.DataFrame(validated)


def detect_price_spikes(
    prices: pd.Series,
    threshold_pct: float = 0.20,  # 20% daily move threshold
) -> pd.Series:
    """Detect suspicious price spikes that may be data errors."""
    returns = prices.pct_change().abs()
    spikes = returns[returns > threshold_pct]
    return spikes
```

### Idempotency — Safe Re-run khi Data Source Gửi Lại

```python
import hashlib
import json
from datetime import datetime

class IdempotentLoader:
    """
    Idempotent ETL: chạy lại cùng data source nhiều lần → kết quả giống nhau.
    Dùng upsert (INSERT OR REPLACE) thay vì INSERT.
    """

    def generate_record_id(self, symbol: str, date: str) -> str:
        """Deterministic ID for deduplication."""
        key = f"{symbol}:{date}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def upsert_ohlcv(self, db_conn, records: list[dict]) -> dict:
        """Insert or update — idempotent."""
        inserted = 0
        updated = 0

        for record in records:
            record_id = self.generate_record_id(record["symbol"], str(record["date"].date()))
            record["id"] = record_id
            record["updated_at"] = datetime.utcnow().isoformat()

            # Upsert: safe to call multiple times
            # SQL: INSERT INTO ohlcv ... ON CONFLICT(id) DO UPDATE SET ...
            # ClickHouse: uses ReplacingMergeTree engine for deduplication
            # Result: always correct, regardless of how many times pipeline runs

        return {"inserted": inserted, "updated": updated, "total": len(records)}

    def check_completeness(
        self,
        db_conn,
        symbol: str,
        expected_dates: pd.DatetimeIndex,
    ) -> list[str]:
        """Find dates with missing data → trigger re-extraction."""
        # Query DB for existing dates
        # Compare with expected trading calendar
        # Return list of missing dates for backfill
        missing_dates = []
        return missing_dates
```

---

## Phần 4: Storage Solutions cho Financial Data

---

### Bảng so sánh Storage

```
┌─────────────────┬──────────────┬─────────────────┬────────────────┬──────────────┐
│ Storage         │ Best For     │ Query Pattern   │ Scale          │ Cost         │
├─────────────────┼──────────────┼─────────────────┼────────────────┼──────────────┤
│ ClickHouse      │ OLAP, fast   │ Aggregations,   │ PB-scale       │ Medium       │
│                 │ aggregation  │ range scans     │ (columnar)     │              │
├─────────────────┼──────────────┼─────────────────┼────────────────┼──────────────┤
│ TimescaleDB     │ Time-series, │ Recent data,    │ TB-scale       │ Low-Medium   │
│                 │ SQL famil.   │ time windows    │ (PostgreSQL)   │              │
├─────────────────┼──────────────┼─────────────────┼────────────────┼──────────────┤
│ Parquet/Arrow   │ Batch jobs,  │ Analytical,     │ Unlimited (S3) │ Very Low     │
│                 │ archival     │ columnar select │                │              │
├─────────────────┼──────────────┼─────────────────┼────────────────┼──────────────┤
│ kdb+            │ HFT, tick    │ Ultra-low       │ TB tick data   │ Very High    │
│                 │ data, ultra  │ latency queries │                │ (proprietary)│
│                 │ low latency  │                 │                │              │
├─────────────────┼──────────────┼─────────────────┼────────────────┼──────────────┤
│ Redis           │ Real-time    │ Key lookup,     │ GB-scale       │ Medium       │
│                 │ cache, L1    │ pub/sub         │ (in-memory)    │              │
└─────────────────┴──────────────┴─────────────────┴────────────────┴──────────────┘

Query Pattern → Storage Decision:
"Give me AAPL price on 2023-01-15"           → Redis (cache) or TimescaleDB
"Average volume by sector, last 30 days"     → ClickHouse (fast aggregation)
"Run strategy backtest on 20 years data"     → Parquet files on S3
"Show real-time bid/ask for 100 symbols"     → kdb+ or Redis
"Store 1B tick records, query by time range" → kdb+ (HFT) or ClickHouse
```

### ClickHouse — Columnar OLAP

```sql
-- ClickHouse schema cho OHLCV (industry best practice)
CREATE TABLE ohlcv (
    symbol      LowCardinality(String),  -- like category — efficient for few unique values
    date        Date,
    open        Float32,
    high        Float32,
    low         Float32,
    close       Float32,
    volume      UInt64,
    adj_close   Float32,
    vwap        Float32,
    updated_at  DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(updated_at)  -- deduplication on background merge
PARTITION BY toYYYYMM(date)             -- partition by month
ORDER BY (symbol, date);                -- sort key = primary index

-- ReplacingMergeTree: tự động deduplicate rows với same ORDER BY key
-- Upsert-safe: insert same (symbol, date) nhiều lần → giữ latest updated_at

-- Aggregate query cực nhanh (columnar reads)
SELECT
    symbol,
    avg(close) as avg_price,
    sum(volume) as total_volume,
    stddevPop(close / neighbor(close, -1) - 1) as daily_vol
FROM ohlcv
WHERE date BETWEEN '2023-01-01' AND '2023-12-31'
GROUP BY symbol
ORDER BY daily_vol DESC
LIMIT 50;
```

```python
import clickhouse_connect
import pandas as pd

def load_ohlcv_clickhouse(
    symbol: str,
    start_date: str,
    end_date: str,
    client: clickhouse_connect.driver.Client,
) -> pd.DataFrame:
    """Fast OHLCV fetch from ClickHouse."""
    query = """
        SELECT symbol, date, open, high, low, close, volume, adj_close
        FROM ohlcv
        WHERE symbol = {symbol:String}
          AND date BETWEEN {start:Date} AND {end:Date}
        ORDER BY date
    """
    result = client.query_df(query, parameters={
        "symbol": symbol,
        "start": start_date,
        "end": end_date,
    })
    return result
```

### Parquet/Arrow — Batch Processing

```python
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
from pathlib import Path

def save_ohlcv_parquet(
    df: pd.DataFrame,
    base_path: str,
    partition_cols: list[str] = ["year", "month"],
) -> None:
    """
    Save OHLCV data as partitioned Parquet.
    Partition structure: /data/ohlcv/year=2023/month=01/data.parquet
    """
    df = df.copy()
    df["year"] = df["date"].dt.year.astype(str)
    df["month"] = df["date"].dt.month.astype(str).str.zfill(2)

    # Define schema with efficient types
    schema = pa.schema([
        pa.field("symbol", pa.dictionary(pa.int16(), pa.string())),
        pa.field("date", pa.date32()),
        pa.field("open", pa.float32()),
        pa.field("high", pa.float32()),
        pa.field("low", pa.float32()),
        pa.field("close", pa.float32()),
        pa.field("volume", pa.int64()),
        pa.field("adj_close", pa.float32()),
    ])

    table = pa.Table.from_pandas(
        df.drop(columns=["year", "month"]),
        schema=schema,
        preserve_index=False,
    )

    pq.write_to_dataset(
        table,
        root_path=base_path,
        partition_cols=partition_cols,
        compression="snappy",          # fast read/write, good compression
        use_dictionary=["symbol"],     # dict encoding for low-cardinality
        data_page_size=1024 * 1024,   # 1MB pages
    )

def read_ohlcv_parquet(
    base_path: str,
    symbols: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """Read with column pruning and partition filtering."""
    import pyarrow.dataset as ds

    dataset = ds.dataset(base_path, format="parquet", partitioning="hive")

    # Pushdown filter — only read relevant partitions
    filters = []
    if start_date:
        filters.append(ds.field("date") >= pa.scalar(pd.Timestamp(start_date).date()))
    if end_date:
        filters.append(ds.field("date") <= pa.scalar(pd.Timestamp(end_date).date()))
    if symbols:
        filters.append(ds.field("symbol").isin(symbols))

    combined_filter = None
    for f in filters:
        combined_filter = f if combined_filter is None else combined_filter & f

    table = dataset.to_table(
        columns=["symbol", "date", "open", "high", "low", "close", "volume"],
        filter=combined_filter,
    )
    return table.to_pandas()

# Compression comparison cho 10,000 stocks × 20 years daily:
# Raw CSV:    ~50 GB
# Parquet Snappy: ~8 GB   (6x compression, fast read)
# Parquet Zstd:   ~5 GB   (10x compression, slightly slower)
# kdb+ binary:    ~3 GB   (industry fastest for tick data)
```

---

## Phần 5: Batch vs Streaming

---

### Batch Processing — End-of-Day, Backtesting

```
Batch Processing:
- Input: bounded dataset (e.g., yesterday's data)
- Trigger: scheduled (daily cron, weekly)
- Latency: minutes to hours (acceptable)
- Use cases:
  * EOD signal computation
  * Backtest execution
  * Factor model rebalancing
  * Historical data normalization

Batch pipeline timeline (EOD):
4:00 PM  Market closes
4:30 PM  Data vendor publishes EOD data
5:00 PM  ETL job runs: fetch → transform → validate → store
6:00 PM  Signal computation job: compute alpha signals for next day
7:00 PM  Portfolio optimization: weights for next day's trading
8:00 PM  Orders generated and sent to execution system
9:30 AM  Next day: orders executed at open
```

### Streaming — Real-time Signals

```
Streaming Processing:
- Input: unbounded stream (continuous ticks)
- Trigger: per event or micro-batch (every 100ms)
- Latency: milliseconds to seconds
- Use cases:
  * Real-time signal computation
  * Live risk monitoring
  * Intraday trading signals
  * Anomaly detection

Streaming pipeline:
Market Feed → Kafka → Stream Processor → Signal Engine → Order Router
             (buffer)  (Flink/Spark     (compute        (execution)
                        Streaming)       alpha real-time)
```

### Lambda Architecture cho Quant Systems

```
Lambda Architecture = Batch Layer + Speed Layer + Serving Layer

┌─────────────────────────────────────────────────────────────────┐
│                    LAMBDA ARCHITECTURE                          │
│                                                                  │
│  Market Data Feed                                               │
│       │                                                         │
│       ├──────────────────────────┐                             │
│       │                          │                             │
│       ▼                          ▼                             │
│  ┌─────────────┐          ┌────────────┐                       │
│  │ SPEED LAYER │          │ BATCH LAYER│                       │
│  │             │          │            │                       │
│  │ Real-time   │          │ Historical │                       │
│  │ signals     │          │ backtests  │                       │
│  │ (Kafka +    │          │ (Spark +   │                       │
│  │  stream     │          │  Parquet)  │                       │
│  │  processing)│          │            │                       │
│  └──────┬──────┘          └─────┬──────┘                       │
│         │                       │                              │
│         └───────────┬───────────┘                              │
│                     │                                          │
│                     ▼                                          │
│              ┌─────────────┐                                   │
│              │SERVING LAYER│                                   │
│              │             │                                   │
│              │ ClickHouse  │ ← Queries from research team      │
│              │ + Redis cache│ ← Real-time dashboard            │
│              └─────────────┘                                   │
└─────────────────────────────────────────────────────────────────┘

Batch views: precomputed for common queries (e.g., factor exposures)
Real-time views: last N minutes, current positions
Serving layer merges both for complete picture
```

### Apache Kafka — Market Data Feeds (Concept)

```
Kafka cho quant systems:

Topics (think: message queues):
  - market.ticks.US      : real-time US equity ticks
  - market.ohlcv.daily   : EOD bars (published ~4:30 PM ET)
  - signals.alpha        : computed alpha signals
  - orders.generated     : portfolio orders

Key properties:
  - Partitioning: partition by symbol → all ticks for AAPL go to same partition
  - Ordering: guaranteed order within partition
  - Replayability: consumers can re-read from any offset
  - Retention: keep last 7 days (ticks), 30 days (bars)

Consumer groups:
  - Signal computation: subscribes to market.ticks.US
  - Risk monitor: subscribes to market.ticks.US, orders.generated
  - Audit log: subscribes to ALL topics
```

```python
# Kafka producer/consumer pattern (conceptual)
from kafka import KafkaProducer, KafkaConsumer
import json

def publish_market_tick(producer: KafkaProducer, tick: dict) -> None:
    """Publish tick to Kafka."""
    producer.send(
        topic="market.ticks.US",
        key=tick["symbol"].encode(),   # partition by symbol
        value=json.dumps(tick).encode(),
    )

def consume_ticks_and_compute_signal(consumer: KafkaConsumer) -> None:
    """Consume ticks and compute real-time signal."""
    price_buffer: dict[str, list[float]] = {}  # symbol → recent prices

    for message in consumer:
        tick = json.loads(message.value)
        symbol = tick["symbol"]
        price = tick["price"]

        if symbol not in price_buffer:
            price_buffer[symbol] = []
        price_buffer[symbol].append(price)

        # Keep rolling window
        if len(price_buffer[symbol]) > 20:
            price_buffer[symbol].pop(0)

        # Compute real-time momentum signal
        if len(price_buffer[symbol]) >= 20:
            prices = price_buffer[symbol]
            momentum = (prices[-1] - prices[0]) / prices[0]
            if abs(momentum) > 0.005:  # 0.5% threshold
                print(f"Signal: {symbol} momentum={momentum:.3%}")
```

---

## Phần 6: Data Quality & Validation

---

### Sanity Checks

```python
import pandas as pd
import numpy as np
from dataclasses import dataclass, field

@dataclass
class DataQualityReport:
    symbol: str
    total_records: int
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return len(self.issues) == 0

def validate_ohlcv_dataframe(
    df: pd.DataFrame,
    symbol: str,
    max_daily_return: float = 0.25,  # 25% daily move = suspicious
    min_volume: int = 1000,
) -> DataQualityReport:
    """Comprehensive OHLCV data quality check."""
    report = DataQualityReport(symbol=symbol, total_records=len(df))

    # 1. Schema checks
    required_cols = {"date", "open", "high", "low", "close", "volume"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        report.issues.append(f"Missing columns: {missing_cols}")
        return report  # can't continue without schema

    # 2. OHLC consistency
    bad_ohlc = df[
        (df["high"] < df["low"]) |
        (df["open"] < df["low"]) | (df["open"] > df["high"]) |
        (df["close"] < df["low"]) | (df["close"] > df["high"])
    ]
    if not bad_ohlc.empty:
        report.issues.append(f"OHLC inconsistency on {len(bad_ohlc)} days: {bad_ohlc['date'].tolist()}")

    # 3. Price spikes
    returns = df["close"].pct_change().abs()
    spikes = df[returns > max_daily_return]
    if not spikes.empty:
        report.warnings.append(
            f"Price spikes (>{max_daily_return:.0%}) on {len(spikes)} days: "
            f"{spikes['date'].tolist()[:5]}"
        )

    # 4. Volume anomalies
    low_volume = df[df["volume"] < min_volume]
    if not low_volume.empty:
        report.warnings.append(f"Low volume (<{min_volume}) on {len(low_volume)} days")

    zero_volume = df[df["volume"] == 0]
    if not zero_volume.empty:
        report.issues.append(f"Zero volume on {len(zero_volume)} days")

    # 5. Missing timestamps (gaps in trading days)
    df_sorted = df.sort_values("date")
    date_diffs = pd.to_datetime(df_sorted["date"]).diff().dt.days
    large_gaps = df_sorted[date_diffs > 5]  # >5 day gap (excluding weekends)
    if not large_gaps.empty:
        report.warnings.append(f"Large date gaps: {large_gaps['date'].tolist()[:3]}")

    # 6. Duplicate dates
    dup_dates = df[df["date"].duplicated()]
    if not dup_dates.empty:
        report.issues.append(f"Duplicate dates: {dup_dates['date'].tolist()}")

    # 7. Non-positive prices
    neg_prices = df[(df["open"] <= 0) | (df["close"] <= 0)]
    if not neg_prices.empty:
        report.issues.append(f"Non-positive prices on {len(neg_prices)} days")

    return report


def run_data_quality_pipeline(
    symbols: list[str],
    data_store: dict[str, pd.DataFrame],
) -> dict[str, DataQualityReport]:
    """Run QC on full universe, surface critical issues."""
    reports = {}
    critical_symbols = []

    for symbol in symbols:
        df = data_store.get(symbol, pd.DataFrame())
        if df.empty:
            reports[symbol] = DataQualityReport(
                symbol=symbol, total_records=0,
                issues=["No data found"]
            )
            critical_symbols.append(symbol)
            continue

        report = validate_ohlcv_dataframe(df, symbol)
        reports[symbol] = report

        if not report.is_clean:
            critical_symbols.append(symbol)

    if critical_symbols:
        # In production: send alert to data engineering team
        print(f"DATA QUALITY ALERT: {len(critical_symbols)} symbols with issues")
        print(f"Symbols: {critical_symbols[:10]}")

    return reports
```

### Schema Validation với Pydantic

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from datetime import date

class OHLCVBatch(BaseModel):
    """Validate incoming data batch."""
    source: Literal["polygon", "bloomberg", "refinitiv", "manual"]
    as_of_date: date
    symbol_count: int = Field(gt=0)
    records: list[dict]
    pipeline_version: str

    @field_validator("records")
    @classmethod
    def validate_records_not_empty(cls, v: list[dict]) -> list[dict]:
        if len(v) == 0:
            raise ValueError("Batch must contain at least 1 record")
        return v

    @field_validator("pipeline_version")
    @classmethod
    def validate_version_format(cls, v: str) -> str:
        import re
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError(f"Version must be semver format (x.y.z), got: {v}")
        return v
```

### Data Lineage Tracking

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class DataSource(str, Enum):
    POLYGON = "polygon"
    BLOOMBERG = "bloomberg"
    REFINITIV = "refinitiv"
    COMPUTED = "computed"

@dataclass
class LineageRecord:
    """Track where each piece of data came from."""
    symbol: str
    date: str
    source: DataSource
    raw_filename: str
    extracted_at: datetime
    transformed_by: str   # pipeline version
    loaded_at: datetime
    record_hash: str      # hash of the record for integrity check

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "date": self.date,
            "source": self.source.value,
            "raw_filename": self.raw_filename,
            "extracted_at": self.extracted_at.isoformat(),
            "transformed_by": self.transformed_by,
            "loaded_at": self.loaded_at.isoformat(),
            "record_hash": self.record_hash,
        }
```

---

## Phần 7: Backtesting Infrastructure

---

### Walk-forward Testing

```
Walk-forward testing: tránh overfitting bằng cách test trên unseen data

Timeline:
──────────────────────────────────────────────────────────────────►

[    TRAIN 1    ][TEST 1]
         [    TRAIN 2    ][TEST 2]
                  [    TRAIN 3    ][TEST 3]
                           [    TRAIN 4    ][TEST 4]

Train window: 3 years data để fit parameters
Test window: 6 months để evaluate
Step: 6 months (then slide forward)

Key: NEVER use TEST data to tune parameters
     TEST data = simulates future trading
```

```python
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Callable

@dataclass
class WalkForwardResult:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    in_sample_sharpe: float
    out_sample_sharpe: float
    best_params: dict

def walk_forward_test(
    prices: pd.DataFrame,
    strategy_fn: Callable[[pd.DataFrame, dict], pd.Series],
    param_grid: list[dict],
    train_years: int = 3,
    test_months: int = 6,
) -> list[WalkForwardResult]:
    """
    Walk-forward testing framework.

    strategy_fn(prices, params) → returns series
    """
    results = []
    prices.index = pd.to_datetime(prices.index)
    start = prices.index[0]
    end = prices.index[-1]

    test_start = start + pd.DateOffset(years=train_years)

    while test_start < end:
        train_end = test_start - pd.Timedelta(days=1)
        test_end = min(test_start + pd.DateOffset(months=test_months), end)

        # In-sample: find best params
        train_data = prices[start:train_end]
        best_sharpe = -np.inf
        best_params = param_grid[0]

        for params in param_grid:
            returns = strategy_fn(train_data, params)
            if returns.std() > 0:
                sharpe = returns.mean() / returns.std() * np.sqrt(252)
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_params = params

        # Out-of-sample: apply best params to test period (NO refitting)
        test_data = prices[test_start:test_end]
        test_returns = strategy_fn(test_data, best_params)
        oos_sharpe = (
            test_returns.mean() / test_returns.std() * np.sqrt(252)
            if test_returns.std() > 0 else 0.0
        )

        results.append(WalkForwardResult(
            train_start=start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            in_sample_sharpe=best_sharpe,
            out_sample_sharpe=oos_sharpe,
            best_params=best_params,
        ))

        # Slide forward
        test_start += pd.DateOffset(months=test_months)

    return results
```

### Transaction Costs và Slippage

```python
import numpy as np

def simulate_transaction_costs(
    trades: np.ndarray,         # position changes (shares)
    prices: np.ndarray,         # prices at execution
    commission_per_share: float = 0.005,    # $0.005/share (Interactive Brokers)
    spread_bps: float = 5.0,               # 5 basis points bid-ask spread
    market_impact_bps: float = 10.0,       # 10 bps market impact for avg trade
    slippage_bps: float = 2.0,             # 2 bps execution slippage
) -> dict:
    """
    Realistic transaction cost model.
    Returns gross_returns, net_returns, total_cost.
    """
    # Commission
    commission = np.abs(trades) * commission_per_share

    # Spread cost (paid on each roundtrip)
    spread_cost = np.abs(trades) * prices * (spread_bps / 10_000) / 2

    # Market impact (depends on trade size vs avg volume — simplified here)
    impact_cost = np.abs(trades) * prices * (market_impact_bps / 10_000)

    # Slippage
    slippage = np.abs(trades) * prices * (slippage_bps / 10_000)

    total_cost = commission + spread_cost + impact_cost + slippage
    total_cost_pct = total_cost / (np.abs(trades) * prices + 1e-8)

    return {
        "commission": commission.sum(),
        "spread": spread_cost.sum(),
        "impact": impact_cost.sum(),
        "slippage": slippage.sum(),
        "total": total_cost.sum(),
        "avg_cost_bps": total_cost_pct.mean() * 10_000,
    }

# Rule of thumb: strategy phải có gross alpha > 2× expected transaction cost
# Nếu backtest Sharpe = 1.5 gross, sau TC thường còn ~0.8-1.0 net
```

### Parallel Backtesting Pattern

```python
from concurrent.futures import ProcessPoolExecutor
import itertools
import numpy as np
import multiprocessing as mp

def run_single_strategy(args: tuple) -> dict:
    """
    Chạy trong subprocess. Args phải serializable (pickle).
    """
    symbol, prices, short_window, long_window = args

    if len(prices) < long_window:
        return {"symbol": symbol, "short": short_window, "long": long_window, "sharpe": np.nan}

    # Simple MA crossover
    returns = np.diff(prices) / prices[:-1]
    ma_short = np.convolve(prices, np.ones(short_window) / short_window, "valid")
    ma_long  = np.convolve(prices, np.ones(long_window)  / long_window,  "valid")

    min_len = min(len(ma_short), len(ma_long))
    signal = np.sign(ma_short[-min_len:] - ma_long[-min_len:])
    strategy_returns = returns[-min_len:] * signal[:-1] if min_len > 1 else np.array([0.0])

    sharpe = (
        strategy_returns.mean() / strategy_returns.std() * np.sqrt(252)
        if strategy_returns.std() > 0 else 0.0
    )
    return {
        "symbol": symbol,
        "short": short_window,
        "long": long_window,
        "sharpe": float(sharpe),
    }

def parameter_sweep_parallel(
    universe: dict[str, np.ndarray],  # symbol → price array
    short_windows: list[int] = [5, 10, 20],
    long_windows: list[int] = [50, 100, 200],
    n_workers: int = mp.cpu_count(),
) -> pd.DataFrame:
    """
    1 strategy × N parameter sets × M stocks = N×M backtests
    Run all in parallel.
    """
    # Generate all (symbol, params) combinations
    args_list = [
        (symbol, prices, short, long_)
        for symbol, prices in universe.items()
        for short, long_ in itertools.product(short_windows, long_windows)
        if short < long_  # constraint: short < long
    ]

    print(f"Running {len(args_list)} backtests on {n_workers} cores...")

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        results = list(executor.map(run_single_strategy, args_list, chunksize=50))

    return pd.DataFrame(results).pivot_table(
        values="sharpe",
        index=["short", "long"],
        columns="symbol",
        aggfunc="mean",
    )

# Storing backtest results
def save_backtest_result(result: dict, storage_path: str) -> str:
    """Save backtest result with metadata for reproducibility."""
    import json, hashlib, datetime

    result_with_meta = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "result": result,
    }
    content = json.dumps(result_with_meta, sort_keys=True, default=str)
    run_id = hashlib.sha256(content.encode()).hexdigest()[:12]

    filepath = f"{storage_path}/{run_id}.json"
    with open(filepath, "w") as f:
        f.write(content)

    return run_id
```

---

## Phần 8: System Design — Full Data Pipeline

---

### Design Problem: "Design a system to ingest, store, and serve daily OHLCV data for 10,000 stocks from 20 years of history"

#### Requirements Analysis

```
Functional Requirements:
- Ingest daily OHLCV for 10,000 stocks (US equities + international)
- 20 years historical data available from day 1
- Support real-time append (each trading day ~4:30 PM ET)
- Serve data for backtesting (full history), research (queries), trading signals

Non-Functional Requirements:
- Historical data load: bulk load 20 years in < 4 hours
- Daily update: ingest + validate + store < 30 minutes after market close
- Query: any stock, any date range, < 500ms response
- Availability: 99.9% uptime (8.7 hours downtime/year)
- Consistency: no look-ahead bias, audit trail for all updates
```

#### Scale Calculations

```
Data Volume:
- 10,000 stocks × 252 trading days/year × 20 years = 50.4M rows
- Per row: ~100 bytes (8 float32 + date + symbol)
- Raw: 50.4M × 100B = ~5 GB (very manageable!)
- With metadata, indices, replicas: ~30 GB total
- Growth: +252 × 10,000 = 2.52M rows/year → +250 MB/year

Parquet compressed: ~500 MB total (10x compression)
ClickHouse: ~2 GB (with indices and replicas)

Query Load:
- Research team: ~50 analysts, each running ~10 queries/hour peak
- = 500 queries/hour = ~8 QPS
- Each query: average 1000 stocks × 1 year = 252,000 rows → sub-second with columnar DB

Update Load:
- Daily: 10,000 rows (one row per stock per day)
- Update window: 4:30 PM - 5:30 PM ET (1 hour window)
- = very low write load
```

#### Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                    OHLCV Data Platform                               │
│                                                                      │
│  Data Sources                                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐                  │
│  │ Polygon  │  │Bloomberg │  │ Manual Overrides  │                  │
│  │ REST API │  │  B-PIPE  │  │ (CSV upload)      │                  │
│  └────┬─────┘  └────┬─────┘  └────────┬──────────┘                  │
│       └─────────────┴─────────────────┘                             │
│                        │                                            │
│                        ▼                                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Ingestion Service                        │    │
│  │                                                             │    │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │    │
│  │  │  Scheduler  │  │   Extractor  │  │   Transformer    │   │    │
│  │  │ (4:30PM ET) │→ │  (async,     │→ │  (validate,      │   │    │
│  │  │  cron job   │  │   parallel)  │  │   adj. corp act) │   │    │
│  │  └─────────────┘  └──────────────┘  └────────┬─────────┘   │    │
│  │                                               │             │    │
│  │  ┌─────────────────────────────────────────── │ ──────────┐ │    │
│  │  │              Quality Gate                  │           │ │    │
│  │  │  ┌──────────┐  ┌───────────┐  ┌───────────▼────────┐  │ │    │
│  │  │  │ Schema   │  │ Sanity   │  │     Alert if        │  │ │    │
│  │  │  │ Validate │  │ Checks   │  │   issues found      │  │ │    │
│  │  │  └──────────┘  └───────────┘  └────────────────────┘  │ │    │
│  │  └────────────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                        │                                            │
│              ┌──────────┼──────────┐                                │
│              ▼          ▼          ▼                                │
│  ┌──────────────┐ ┌──────────┐ ┌──────────┐                        │
│  │  ClickHouse  │ │ Parquet  │ │  Redis   │                        │
│  │  (OLAP, fast │ │  on S3   │ │  (latest │                        │
│  │   queries)   │ │ (archive,│ │   prices │                        │
│  │              │ │  batch)  │ │   cache) │                        │
│  └──────┬───────┘ └──────────┘ └──────────┘                        │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │                    Serving Layer                         │       │
│  │                                                          │       │
│  │  ┌────────────────┐  ┌────────────────┐                 │       │
│  │  │  Query API     │  │  Python SDK    │                 │       │
│  │  │  (FastAPI)     │  │  (research)    │                 │       │
│  │  │  /ohlcv/{sym}  │  │  get_prices()  │                 │       │
│  │  └────────────────┘  └────────────────┘                 │       │
│  └──────────────────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────────────┘
```

#### Trade-offs Discussion

```
ClickHouse vs TimescaleDB:
→ ClickHouse: better for OLAP aggregations (factor exposure across 10K stocks)
→ TimescaleDB: better for time-window queries, familiar SQL, easier ops
→ Decision: ClickHouse (quant research needs cross-sectional aggregations)

Single DB vs Parquet + DB:
→ Parquet: cheaper storage, portable, good for bulk backtest jobs
→ DB: better for ad-hoc queries, lower latency
→ Decision: both — Parquet as archival/batch, ClickHouse for interactive queries

Push vs Pull for daily updates:
→ Push: data vendor sends data → lower latency
→ Pull: we poll vendor API → more control, easier retry
→ Decision: pull with scheduled job (simpler, vendor-agnostic)

Redis cache layer:
→ Cache "latest close price" for each stock (10K entries × ~100B = 1MB)
→ TTL: 24 hours (invalidate at next EOD update)
→ Eliminates DB queries for most common access pattern
```

---

## Phần 9: Interview Q&A — Data Engineering for Quant

---

### Q1: "What is look-ahead bias and how do you prevent it?"

**Trả lời:**

Look-ahead bias là khi backtest vô tình sử dụng thông tin từ tương lai mà trader KHÔNG CÓ tại thời điểm trading.

**Ví dụ cụ thể:**
- Company A reports earnings on Nov 15. Backtest trade on Nov 1 based on "Q3 data" — nhưng Q3 data chưa được released!
- Dùng full-day OHLCV Close price để generate signal cho cùng ngày đó — nhưng Close price chỉ biết khi market đóng cửa!

**Cách prevent:**

1. **Point-in-time database**: mỗi record có `release_date` riêng. Query chỉ lấy data với `release_date <= backtest_date`.

2. **Timestamp discipline**: signal tại ngày T chỉ được dùng data từ T-1 trở về trước (Close price của T-1 là giá đóng cửa ngày hôm qua).

```python
# WRONG: dùng same-day close để generate signal
signal_t = compute_signal(close_price_t)   # close_t chưa biết lúc open!
execute_trade_at_open_t(signal_t)          # BUG: look-ahead!

# CORRECT: signal dùng yesterday's close, trade at today's open
signal_t = compute_signal(close_price_t_minus_1)  # known before open
execute_trade_at_open_t(signal_t)                  # correct!
```

3. **Walk-forward testing**: chỉ fit parameters trên training window, evaluate trên future test window.

4. **Audit checklist:**
   - Tất cả data có `release_date` không?
   - Signal chỉ dùng data từ trước execution time không?
   - Universe được filtered theo point-in-time membership không?

---

### Q2: "How do you handle corporate actions in historical price data?"

**Trả lời:**

Corporate actions (splits, dividends, mergers) làm cho raw historical prices không comparable. Phải adjust.

**Nguyên tắc: adjust BACKWARD từ hiện tại.**

```python
def build_adjusted_price_series(
    raw_prices: pd.Series,
    corporate_actions: list[dict],
) -> pd.Series:
    """
    Build backward-adjusted price series.
    All historical prices expressed in terms of today's shares.

    Example: 4:1 split on 2020-06-12
    - All prices BEFORE 2020-06-12 are divided by 4
    - Prices AFTER 2020-06-12 unchanged
    → Now series is comparable (all in "post-split share" units)
    """
    adjusted = raw_prices.copy().astype(float)

    # Sort actions descending (adjust from most recent backward)
    sorted_actions = sorted(corporate_actions, key=lambda x: x["date"], reverse=True)

    for action in sorted_actions:
        action_date = pd.Timestamp(action["date"])
        action_type = action["type"]

        if action_type == "split":
            ratio = action["ratio"]  # e.g. 4.0 for 4:1 split
            mask = adjusted.index < action_date
            adjusted[mask] /= ratio

        elif action_type == "dividend":
            div = action["amount"]
            # Price on ex-date
            if action_date in adjusted.index:
                price = adjusted[action_date]
                if price > div:
                    factor = (price - div) / price
                    mask = adjusted.index < action_date
                    adjusted[mask] *= factor

    return adjusted

# Important: VOLUME must also be adjusted for splits
def adjust_volume_for_splits(volume: pd.Series, splits: list[dict]) -> pd.Series:
    adjusted_vol = volume.copy().astype(float)
    for split in sorted(splits, key=lambda x: x["date"], reverse=True):
        split_date = pd.Timestamp(split["date"])
        mask = adjusted_vol.index < split_date
        adjusted_vol[mask] *= split["ratio"]  # volume increases with split
    return adjusted_vol
```

**Key points:**
- Adjusted prices: backward-adjusted từ present → past comparisons correct
- Volume phải adjust ngược chiều split ratio
- Cần source of truth cho corporate actions (Bloomberg Corporate Action API, Compustat)
- Luôn lưu cả raw prices VÀ adjusted prices để audit

---

### Q3: "Design a real-time data pipeline for live market data"

**Trả lời:**

```
High-level design:

Market Exchange/ECN
       │
       │ (FIX protocol / Websocket)
       ▼
  Market Data Feed Handler
  - Subscribe to symbols
  - Parse FIX/binary messages
  - Normalize to standard format
       │
       ▼
  Apache Kafka (buffer + fan-out)
  Topic: market.ticks.{exchange}
  Partitioned by: symbol
  Retention: 24 hours
       │
       ├──────────────────────┬─────────────────────┐
       ▼                      ▼                     ▼
  Signal Engine          Risk Monitor         Market Data Store
  - Rolling calcs        - Position limits    - Redis (latest price)
  - Alpha signals        - VaR real-time      - ClickHouse (history)
       │                      │
       ▼                      ▼
  Order Generator        Circuit Breaker
  - Portfolio            - Stop trading if
    optimization           risk limits hit
       │
       ▼
  Order Management System (OMS)
  - Smart order routing
  - Execution algorithms
```

```python
import asyncio
import redis.asyncio as redis
from dataclasses import dataclass

@dataclass
class RealTimePriceFeed:
    """Core real-time price serving."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.price_cache: dict[str, float] = {}

    async def update_price(self, symbol: str, price: float, volume: int) -> None:
        """Update latest price in Redis on each tick."""
        await self.redis.hset(
            "latest_prices",
            mapping={symbol: str(price)},
        )
        await self.redis.expire("latest_prices", 86400)  # expire after market close + buffer

    async def get_price(self, symbol: str) -> float | None:
        """Sub-millisecond price lookup from Redis."""
        price = await self.redis.hget("latest_prices", symbol)
        return float(price) if price else None

    async def get_all_prices(self, symbols: list[str]) -> dict[str, float]:
        """Batch lookup."""
        prices = await self.redis.hmget("latest_prices", *symbols)
        return {
            sym: float(p) for sym, p in zip(symbols, prices) if p is not None
        }
```

---

### Q4: "How would you backtest a strategy across 1000 stocks × 20 years?"

**Trả lời:**

```
Scale:
- 1000 stocks × 252 days × 20 years = 5.04M data points
- Manageable: fits in RAM as float32 matrix (1000 × 5040 × 4 bytes = ~20 MB)

Architecture approach:

1. Load data as numpy matrix (vectorized from parquet)
   prices_matrix: shape (5040, 1000)  # days × stocks

2. Vectorize signal computation
   # NEVER loop over stocks — use matrix operations
   returns = np.diff(prices_matrix, axis=0) / prices_matrix[:-1, :]   # (5039, 1000)
   ma_20   = pd.DataFrame(prices_matrix).rolling(20).mean().values     # (5040, 1000)
   signal  = np.sign(prices_matrix - ma_20)                            # (5040, 1000)

3. Portfolio simulation (matrix multiply)
   weights = signal / signal.shape[1]  # equal weight among long signals
   portfolio_returns = (returns * weights[:-1, :]).sum(axis=1)  # (5039,)

4. If parameter sweep needed → ProcessPoolExecutor
   - Each worker: different (short, long) window pair
   - Worker receives price matrix → computes internally (no large data transfer)
   - Returns only scalar metrics (Sharpe, return, drawdown)

5. Store results in structured format
   pd.DataFrame(results).to_parquet("sweep_results.parquet")
```

```python
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor

def vectorized_backtest_full_universe(
    prices: np.ndarray,     # shape: (n_days, n_stocks)
    short_window: int = 10,
    long_window: int = 50,
) -> dict:
    """
    Full universe backtest using matrix operations.
    No Python loops over stocks or days.
    """
    n_days, n_stocks = prices.shape

    # Daily returns matrix
    returns = np.diff(prices, axis=0) / (prices[:-1, :] + 1e-8)

    # Moving averages (vectorized across all stocks simultaneously)
    prices_df = pd.DataFrame(prices)
    ma_short = prices_df.rolling(short_window).mean().values  # (n_days, n_stocks)
    ma_long  = prices_df.rolling(long_window).mean().values   # (n_days, n_stocks)

    # Signal: +1 long, -1 short, 0 no position
    signal = np.sign(ma_short - ma_long)  # (n_days, n_stocks)
    signal[:long_window, :] = 0  # no signal before warmup

    # Equal-weight portfolio of long signals
    n_long = (signal > 0).sum(axis=1, keepdims=True).clip(min=1)
    weights = np.where(signal > 0, 1.0 / n_long, 0.0)

    # Portfolio daily returns
    portfolio_returns = (returns * weights[:-1, :]).sum(axis=1)

    # Metrics
    sharpe = portfolio_returns.mean() / (portfolio_returns.std() + 1e-8) * np.sqrt(252)
    cumulative = np.cumprod(1 + portfolio_returns)
    total_return = float(cumulative[-1] - 1)
    running_max = np.maximum.accumulate(cumulative)
    max_drawdown = float(((cumulative - running_max) / running_max).min())

    return {
        "sharpe": float(sharpe),
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "n_days": n_days,
        "n_stocks": n_stocks,
    }

if __name__ == "__main__":
    # Simulate 1000 stocks × 20 years
    n_days, n_stocks = 252 * 20, 1000
    prices = np.random.randn(n_days, n_stocks).cumsum(axis=0) + 100
    prices = np.abs(prices) + 50  # ensure positive

    import time
    start = time.perf_counter()
    result = vectorized_backtest_full_universe(prices)
    elapsed = time.perf_counter() - start

    print(f"1000 stocks × 20 years backtest: {elapsed:.2f}s")  # < 5s
    print(f"Sharpe: {result['sharpe']:.2f}")
    print(f"Total Return: {result['total_return']:.1%}")
    print(f"Max Drawdown: {result['max_drawdown']:.1%}")
```

---

*Tổng hợp: Module 03 bao gồm toàn bộ kiến thức data pipeline cho quant engineering — từ financial data types, time-series challenges, ETL design, storage trade-offs, batch vs streaming, đến system design và 4 interview Q&A chuẩn WorldQuant-level. Kết hợp với Module 02 (Python Performance) để có full picture cho engineering interview.*
