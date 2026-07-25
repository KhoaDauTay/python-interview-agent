# Module 02: Python Performance & Scale — WorldQuant Interview Prep

> Mức độ: Medium → Hard | Phù hợp: Quant Engineering / Research Engineer roles tại WorldQuant

---

## Phần 1: GIL (Global Interpreter Lock)

---

### Lý thuyết: GIL là gì và tại sao CPython có nó?

**GIL là gì:**
GIL (Global Interpreter Lock) là một mutex bảo vệ truy cập vào Python objects, đảm bảo rằng tại mỗi thời điểm chỉ có một thread Python nào được thực thi bytecode. Đây là cơ chế của CPython (implementation chính thức bằng C), không phải của ngôn ngữ Python nói chung.

**Tại sao CPython có GIL:**
- CPython dùng **reference counting** để quản lý memory. Nếu nhiều threads cùng thay đổi ref count của cùng một object mà không có lock, sẽ có race condition → memory leak hoặc segfault.
- GIL làm cho reference counting thread-safe mà không cần lock riêng cho từng object (sẽ rất chậm).
- Lợi ích thứ hai: đơn giản hóa việc tích hợp C extensions — C code không cần worry về thread safety của Python objects.

**GIL ảnh hưởng thế nào:**

```
CPU-bound (thuần Python):
Thread 1: [run][run][run][run][release][........waiting........][acquire][run]
Thread 2: [........waiting........][acquire][run][run][release][........]
→ Không có speedup — chỉ 1 thread chạy tại mỗi thời điểm
→ Thậm chí chậm hơn do overhead context switching

I/O-bound (network, disk):
Thread 1: [run][await I/O → RELEASE GIL][................][acquire][run]
Thread 2: [........][acquire GIL][run][run][await I/O → RELEASE GIL][..]
→ Threads overlap khi waiting I/O → speedup thực sự
```

**Khi nào GIL KHÔNG phải vấn đề:**
1. **I/O-bound workloads**: GIL được release khi thread chờ I/O (network, file, database). Threading hoạt động tốt.
2. **NumPy/SciPy operations**: C extensions release GIL khi thực hiện computation nặng. `np.dot()` chạy parallel thực sự.
3. **Multiprocessing**: mỗi process có Python interpreter riêng → không có GIL shared.
4. **PyPy**: JIT-compiled, có GIL nhưng nhanh hơn nhiều. Một số implementations không có GIL.
5. **Python 3.13+**: thực nghiệm "free-threaded" mode (`--disable-gil`) — watch out trong vài năm tới.

```python
import threading
import time
import numpy as np

# GIL KHÔNG giải phóng — pure Python CPU work
def count_up(n: int) -> None:
    total = 0
    for _ in range(n):
        total += 1

# GIL ĐƯỢC giải phóng — numpy C extension
def numpy_work(size: int) -> float:
    arr = np.random.randn(size, size)
    return float(np.linalg.norm(arr))

# Benchmark: threading vs sequential cho CPU-bound
N = 5_000_000

start = time.perf_counter()
count_up(N)
count_up(N)
seq_time = time.perf_counter() - start

start = time.perf_counter()
t1 = threading.Thread(target=count_up, args=(N,))
t2 = threading.Thread(target=count_up, args=(N,))
t1.start(); t2.start()
t1.join(); t2.join()
thread_time = time.perf_counter() - start

print(f"Sequential: {seq_time:.2f}s")   # e.g. 0.40s
print(f"Threading:  {thread_time:.2f}s") # e.g. 0.42s — NO speedup, slightly slower!
```

---

## Phần 2: Concurrency Models — Chọn cái nào?

---

### Bảng so sánh tổng quan

```
┌─────────────────────┬───────────────────┬──────────────────┬────────────────────┐
│ Model               │ Use case          │ GIL impact       │ Memory             │
├─────────────────────┼───────────────────┼──────────────────┼────────────────────┤
│ asyncio             │ I/O-bound, high   │ Single-threaded  │ Shared             │
│                     │ concurrency       │ — no GIL issue   │ (efficient)        │
├─────────────────────┼───────────────────┼──────────────────┼────────────────────┤
│ threading           │ I/O-bound, legacy │ Released on I/O  │ Shared             │
│                     │ blocking APIs     │ — OK for I/O     │ (watch race cond.) │
├─────────────────────┼───────────────────┼──────────────────┼────────────────────┤
│ multiprocessing     │ CPU-bound,        │ Bypassed — each  │ Separate (pickle   │
│                     │ heavy compute     │ process own GIL  │ overhead)          │
├─────────────────────┼───────────────────┼──────────────────┼────────────────────┤
│ concurrent.futures  │ Both — higher     │ Depends on       │ Depends on         │
│ ThreadPoolExecutor  │ level API         │ executor type    │ executor type      │
│ ProcessPoolExecutor │                   │                  │                    │
└─────────────────────┴───────────────────┴──────────────────┴────────────────────┘
```

### asyncio — I/O-bound, event loop, coroutines

```python
import asyncio
import aiohttp
import time

# asyncio: concurrent I/O bằng single thread
async def fetch_price(session: aiohttp.ClientSession, symbol: str) -> dict:
    """Simulate fetching price from data vendor API."""
    await asyncio.sleep(0.1)  # simulate network I/O
    return {"symbol": symbol, "price": 100.0}

async def fetch_all_prices(symbols: list[str]) -> list[dict]:
    """Fetch 1000 symbols concurrently — asyncio tối ưu cho pattern này."""
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_price(session, sym) for sym in symbols]
        # gather tất cả concurrently — chỉ mất ~0.1s dù có 1000 symbols
        return await asyncio.gather(*tasks)

async def main():
    symbols = [f"STOCK_{i}" for i in range(1000)]
    start = time.perf_counter()
    prices = await fetch_all_prices(symbols)
    elapsed = time.perf_counter() - start
    print(f"Fetched {len(prices)} prices in {elapsed:.2f}s")  # ~0.1s

asyncio.run(main())
```

### threading — I/O-bound, legacy blocking APIs

```python
import threading
import requests  # blocking library — dùng với threading
import time
from queue import Queue

def fetch_price_blocking(symbol: str, result_queue: Queue) -> None:
    """Blocking I/O — GIL được release khi chờ network."""
    import time; time.sleep(0.1)  # simulate blocking I/O
    result_queue.put({"symbol": symbol, "price": 100.0})

def fetch_with_threads(symbols: list[str]) -> list[dict]:
    result_queue: Queue = Queue()
    threads = [
        threading.Thread(target=fetch_price_blocking, args=(sym, result_queue))
        for sym in symbols
    ]
    for t in threads: t.start()
    for t in threads: t.join()
    return [result_queue.get() for _ in symbols]
```

### multiprocessing — CPU-bound, bypass GIL

```python
import multiprocessing as mp
import numpy as np
from typing import Tuple

def compute_factor_exposure(args: Tuple[str, np.ndarray]) -> dict:
    """
    CPU-intensive computation — chạy trong separate process.
    Mỗi process có Python interpreter riêng → không bị GIL.
    """
    symbol, returns = args
    # Heavy CPU work: rolling regression, factor decomposition, etc.
    mean = float(np.mean(returns))
    std = float(np.std(returns))
    sharpe = mean / std * np.sqrt(252) if std > 0 else 0.0
    # Simulate heavy computation
    cov_matrix = np.cov(returns.reshape(1, -1))
    return {"symbol": symbol, "sharpe": sharpe, "vol": std}

def parallel_factor_computation(
    symbols: list[str],
    returns_data: dict[str, np.ndarray],
    n_workers: int = 4,
) -> list[dict]:
    """Parallel computation across stocks."""
    args_list = [(sym, returns_data[sym]) for sym in symbols]

    with mp.Pool(processes=n_workers) as pool:
        results = pool.map(compute_factor_exposure, args_list)

    return results
```

### concurrent.futures — High-level API, ThreadPoolExecutor vs ProcessPoolExecutor

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import numpy as np
import time

# ThreadPoolExecutor — I/O-bound hoặc numpy (C extension releases GIL)
def download_market_data(symbol: str) -> dict:
    """Blocking I/O — tốt với ThreadPoolExecutor."""
    time.sleep(0.05)  # simulate API call
    return {"symbol": symbol, "data": np.random.randn(252)}

# ProcessPoolExecutor — CPU-bound pure Python
def backtest_strategy(params: dict) -> dict:
    """CPU-bound — tốt với ProcessPoolExecutor."""
    returns = np.random.randn(252 * 10)  # 10 years
    sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(252))
    return {"params": params, "sharpe": sharpe}

def parallel_data_download(symbols: list[str]) -> list[dict]:
    """I/O-bound: ThreadPoolExecutor."""
    results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_symbol = {
            executor.submit(download_market_data, sym): sym
            for sym in symbols
        }
        for future in as_completed(future_to_symbol):
            sym = future_to_symbol[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Error for {sym}: {e}")
    return results

def parallel_parameter_sweep(param_grid: list[dict]) -> list[dict]:
    """CPU-bound: ProcessPoolExecutor."""
    with ProcessPoolExecutor(max_workers=mp.cpu_count()) as executor:
        futures = [executor.submit(backtest_strategy, params) for params in param_grid]
        results = [f.result() for f in futures]
    return results

# Ví dụ thực tế: parallel data processing cho backtest
def process_universe_parallel(
    symbols: list[str],
    n_workers: int = 8,
) -> dict[str, np.ndarray]:
    """
    Backtest pattern: download data concurrently (I/O),
    then compute signals in parallel (CPU).
    """
    # Step 1: Parallel download (I/O-bound → ThreadPool)
    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        data_futures = {sym: executor.submit(download_market_data, sym) for sym in symbols}
        raw_data = {sym: future.result()["data"] for sym, future in data_futures.items()}

    # Step 2: Parallel signal computation (CPU-bound → ProcessPool)
    args = [(sym, data) for sym, data in raw_data.items()]
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        signal_futures = [executor.submit(compute_factor_exposure, arg) for arg in args]
        signals = [f.result() for f in signal_futures]

    return {s["symbol"]: s for s in signals}
```

---

## Phần 3: NumPy Vectorization

---

### Tại sao Python loop chậm, NumPy nhanh

**Python loop:**
- Mỗi iteration: interpreter overhead, type checking, object creation, reference counting
- Mỗi số nguyên Python là một object ~28 bytes
- Không tận dụng được CPU cache locality

**NumPy:**
- C backend: operations chạy compiled C code trực tiếp
- SIMD (Single Instruction Multiple Data): CPU instructions xử lý nhiều phần tử cùng lúc (AVX2: 8 floats/cycle)
- Contiguous memory: cache-friendly, CPU prefetcher hoạt động hiệu quả
- Release GIL: cho phép threading thực sự

```python
import numpy as np
import time

# Benchmark: Python loop vs NumPy
def python_returns(prices: list[float]) -> list[float]:
    """Pure Python — chậm."""
    returns = []
    for i in range(1, len(prices)):
        returns.append((prices[i] - prices[i-1]) / prices[i-1])
    return returns

def numpy_returns(prices: np.ndarray) -> np.ndarray:
    """NumPy vectorized — nhanh."""
    return np.diff(prices) / prices[:-1]

# Generate test data
n = 1_000_000
prices_list = [100.0 + i * 0.01 + np.random.randn() * 0.5 for i in range(n)]
prices_arr = np.array(prices_list)

# Benchmark
start = time.perf_counter()
ret_python = python_returns(prices_list)
t_python = time.perf_counter() - start

start = time.perf_counter()
ret_numpy = numpy_returns(prices_arr)
t_numpy = time.perf_counter() - start

print(f"Python loop: {t_python:.3f}s")   # ~0.5s
print(f"NumPy:       {t_numpy:.4f}s")    # ~0.003s
print(f"Speedup:     {t_python/t_numpy:.0f}x")  # ~150-200x
```

### Moving Average — 3 cách, từ chậm đến nhanh

```python
import numpy as np
import time

prices = np.random.randn(100_000).cumsum() + 100

# Cách 1: Python loop (chậm nhất)
def moving_avg_loop(prices: np.ndarray, window: int) -> np.ndarray:
    n = len(prices)
    result = np.full(n, np.nan)
    for i in range(window - 1, n):
        result[i] = np.mean(prices[i - window + 1 : i + 1])
    return result

# Cách 2: np.convolve (nhanh)
def moving_avg_convolve(prices: np.ndarray, window: int) -> np.ndarray:
    weights = np.ones(window) / window
    ma = np.convolve(prices, weights, mode="valid")
    # Pad với NaN ở đầu để align với original
    return np.concatenate([np.full(window - 1, np.nan), ma])

# Cách 3: stride tricks (fastest — zero-copy view)
def moving_avg_stride(prices: np.ndarray, window: int) -> np.ndarray:
    from numpy.lib.stride_tricks import sliding_window_view
    windows = sliding_window_view(prices, window_shape=window)
    ma = windows.mean(axis=-1)
    return np.concatenate([np.full(window - 1, np.nan), ma])

# Cách 4: pandas rolling (practical, readable)
import pandas as pd
def moving_avg_pandas(prices: np.ndarray, window: int) -> np.ndarray:
    return pd.Series(prices).rolling(window).mean().values

# Benchmark
window = 20
for name, func in [
    ("Loop", moving_avg_loop),
    ("Convolve", moving_avg_convolve),
    ("Stride tricks", moving_avg_stride),
    ("Pandas rolling", moving_avg_pandas),
]:
    start = time.perf_counter()
    result = func(prices, window)
    elapsed = time.perf_counter() - start
    print(f"{name:15s}: {elapsed*1000:.2f}ms")
```

### Broadcasting Rules

```python
import numpy as np

# Broadcasting rule: dimensions align from right, size 1 stretches
# Shape (N,) + (1,) → (N,)   OK
# Shape (N, M) + (M,) → (N, M)  OK — (M,) treated as (1, M)
# Shape (N, M) + (N,)  → ERROR  (need reshape to (N, 1))

# Ví dụ quant: normalize returns across stocks
returns = np.random.randn(252, 500)   # 252 days × 500 stocks

# Cross-sectional z-score (normalize across stocks each day)
daily_mean = returns.mean(axis=1, keepdims=True)   # (252, 1)
daily_std  = returns.std(axis=1, keepdims=True)    # (252, 1)
z_scores = (returns - daily_mean) / daily_std      # (252, 500) broadcasting

# Time-series normalization (normalize each stock's history)
stock_mean = returns.mean(axis=0)   # (500,)
stock_std  = returns.std(axis=0)    # (500,)
normalized = (returns - stock_mean) / stock_std  # (252, 500) — auto broadcast

# Portfolio weighted returns
weights = np.array([0.02] * 500)          # (500,)
portfolio_returns = (returns * weights).sum(axis=1)  # (252,)
```

### Common Patterns: rolling calculations, normalization, filtering

```python
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

prices = np.random.randn(1000).cumsum() + 100

# Rolling Sharpe ratio (window=60 days)
returns = np.diff(prices) / prices[:-1]
window = 60
rolling_windows = sliding_window_view(returns, window_shape=window)
rolling_mean = rolling_windows.mean(axis=-1)
rolling_std  = rolling_windows.std(axis=-1)
rolling_sharpe = rolling_mean / (rolling_std + 1e-8) * np.sqrt(252)

# Rank-based normalization (common in factor investing)
def rank_normalize(arr: np.ndarray) -> np.ndarray:
    """Convert values to uniform ranks in [-0.5, 0.5]."""
    n = len(arr)
    ranks = arr.argsort().argsort()  # double argsort = rank
    return (ranks / (n - 1)) - 0.5

# Filter stocks with positive momentum
momentum = returns[-20:].mean(axis=0) if returns.ndim > 1 else returns[-20:].mean()
mask = momentum > 0
selected_returns = returns[:, mask] if returns.ndim > 1 else returns[mask]

# Vectorized correlation matrix
corr_matrix = np.corrcoef(returns.T if returns.ndim > 1 else returns)
```

### Memory Layout: C-contiguous vs F-contiguous

```python
import numpy as np

# C-contiguous (row-major): default NumPy layout
# Dữ liệu được lưu hàng-theo-hàng: arr[0,0], arr[0,1], arr[1,0], arr[1,1]
c_arr = np.zeros((1000, 500), order='C')  # default
print(c_arr.flags['C_CONTIGUOUS'])  # True

# F-contiguous (column-major): Fortran layout
# Dữ liệu lưu cột-theo-cột: arr[0,0], arr[1,0], arr[0,1], arr[1,1]
f_arr = np.zeros((1000, 500), order='F')
print(f_arr.flags['F_CONTIGUOUS'])  # True

# Quant context: time × stocks matrix
# C-contiguous → row access (per day operations) nhanh
# F-contiguous → column access (per stock operations) nhanh
returns = np.random.randn(252, 500)  # C-contiguous

# Row slice (per day) — fast với C-contiguous
day_returns = returns[100, :]  # single day's cross-section

# Column slice (per stock) — slow với C-contiguous, consider transpose or F-order
stock_ts = returns[:, 50]  # single stock's time series

# Để cross-stock operations nhanh, có thể dùng:
returns_T = np.asfortranarray(returns)  # convert to F-contiguous
# Hoặc simply returns.T → F-contiguous view
```

---

## Phần 4: Pandas Performance

---

### Sai lầm phổ biến và cách sửa

```python
import pandas as pd
import numpy as np
import time

# Tạo sample data
n = 100_000
df = pd.DataFrame({
    "symbol": np.random.choice(["AAPL", "GOOG", "MSFT", "AMZN"], n),
    "price": np.random.randn(n) * 10 + 100,
    "volume": np.random.randint(1000, 1_000_000, n),
    "returns": np.random.randn(n) * 0.02,
})

# BAD: iterrows — rất chậm, hàng trăm ms cho 100k rows
def calc_signal_iterrows(df: pd.DataFrame) -> pd.Series:
    signals = []
    for idx, row in df.iterrows():  # iterrows tạo Series mỗi row — SLOW
        if row["returns"] > 0 and row["volume"] > 500_000:
            signals.append(row["returns"] * 2)
        else:
            signals.append(0.0)
    return pd.Series(signals)

# BAD: apply (khi có thể vectorize)
def calc_signal_apply(df: pd.DataFrame) -> pd.Series:
    def row_logic(row):  # Python function called for each row
        if row["returns"] > 0 and row["volume"] > 500_000:
            return row["returns"] * 2
        return 0.0
    return df.apply(row_logic, axis=1)  # axis=1 = per row — SLOW

# GOOD: vectorized (dùng NumPy operations trực tiếp trên columns)
def calc_signal_vectorized(df: pd.DataFrame) -> pd.Series:
    mask = (df["returns"] > 0) & (df["volume"] > 500_000)
    return np.where(mask, df["returns"] * 2, 0.0)

# BETTER: assign back to avoid chained indexing
def calc_signal_best(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    mask = (df["returns"] > 0) & (df["volume"] > 500_000)
    df["signal"] = np.where(mask, df["returns"] * 2, 0.0)
    return df

# Benchmark
for name, func in [
    # ("iterrows", calc_signal_iterrows),  # too slow, skip
    ("apply", calc_signal_apply),
    ("vectorized", calc_signal_vectorized),
]:
    start = time.perf_counter()
    result = func(df)
    elapsed = time.perf_counter() - start
    print(f"{name:15s}: {elapsed*1000:.1f}ms")
# apply:       ~3000ms
# vectorized:  ~5ms     → 600x faster
```

### Cheatsheet: iterrows vs apply vs vectorize vs Cython

```
┌─────────────────┬───────────┬────────────────────────────────────────────┐
│ Method          │ Speed     │ Khi nào dùng                               │
├─────────────────┼───────────┼────────────────────────────────────────────┤
│ iterrows()      │ ★☆☆☆☆     │ NEVER — debug only, < 100 rows             │
│ itertuples()    │ ★★☆☆☆     │ Legacy code, khi phải dùng Python loop     │
│ apply(axis=1)   │ ★★☆☆☆     │ Complex row logic không vectorize được     │
│ apply(axis=0)   │ ★★★☆☆     │ Column-wise operations                     │
│ Vectorized      │ ★★★★☆     │ Default choice — np.where, boolean masks   │
│ Cython/Numba    │ ★★★★★     │ Critical path, extreme performance needed  │
└─────────────────┴───────────┴────────────────────────────────────────────┘
```

### Memory Optimization: dtypes và categories

```python
import pandas as pd
import numpy as np

# Original dtypes — wasteful
df = pd.DataFrame({
    "symbol": ["AAPL", "GOOG", "MSFT"] * 100_000,  # object dtype ~ 50 bytes/entry
    "date": pd.date_range("2020-01-01", periods=300_000, freq="s"),
    "price": np.random.randn(300_000) * 10 + 100,   # float64 — fine
    "volume": np.random.randint(0, 1_000_000, 300_000),  # int64
    "exchange": np.random.choice(["NYSE", "NASDAQ"], 300_000),
})

print(f"Memory before: {df.memory_usage(deep=True).sum() / 1e6:.1f} MB")

# Optimize
df_opt = df.copy()
df_opt["symbol"] = df_opt["symbol"].astype("category")     # saves ~70% for few unique values
df_opt["exchange"] = df_opt["exchange"].astype("category")  # only 2 unique values!
df_opt["volume"] = df_opt["volume"].astype("int32")         # int64→int32 halves memory
df_opt["price"] = df_opt["price"].astype("float32")         # float64→float32 halves memory
# Note: float32 loses precision — OK for many quant uses, not for high-precision calc

print(f"Memory after:  {df_opt.memory_usage(deep=True).sum() / 1e6:.1f} MB")
# Thường giảm 50-80% memory

# Kiểm tra unique values để quyết định có nên dùng category không
for col in df.select_dtypes("object").columns:
    n_unique = df[col].nunique()
    total = len(df)
    ratio = n_unique / total
    print(f"{col}: {n_unique} unique / {total} total ({ratio:.1%}) → "
          f"{'category' if ratio < 0.5 else 'keep object'}")
```

### Chunking Large Files

```python
import pandas as pd
import numpy as np
from typing import Iterator

# Xử lý file 10GB tick data không bị OOM
def process_large_csv(
    filepath: str,
    chunk_size: int = 100_000,
) -> pd.DataFrame:
    """Đọc và xử lý file lớn theo từng chunk."""
    results = []

    for chunk in pd.read_csv(
        filepath,
        chunksize=chunk_size,
        dtype={
            "symbol": "category",
            "price": "float32",
            "volume": "int32",
        },
        parse_dates=["timestamp"],
    ):
        # Xử lý từng chunk
        chunk = chunk[chunk["volume"] > 0]  # filter bad data
        chunk["returns"] = chunk.groupby("symbol")["price"].pct_change()
        # Aggregate: chỉ giữ summary statistics per chunk
        summary = chunk.groupby("symbol").agg({
            "returns": ["mean", "std", "count"],
            "volume": "sum",
        })
        results.append(summary)

    # Combine summaries (small — có thể fit in memory)
    return pd.concat(results).groupby(level=0).sum()

# Generator pattern cho streaming processing
def stream_market_data(filepath: str, chunk_size: int = 10_000) -> Iterator[pd.DataFrame]:
    """Yield chunks lazily — caller chọn cách xử lý."""
    for chunk in pd.read_csv(filepath, chunksize=chunk_size):
        yield chunk

# Dùng với pipeline
def compute_daily_vwap(filepath: str) -> pd.DataFrame:
    """Volume-Weighted Average Price từ tick data."""
    vwap_data = []
    for chunk in stream_market_data(filepath):
        chunk["pv"] = chunk["price"] * chunk["volume"]
        daily = chunk.groupby(["date", "symbol"]).agg(
            pv_sum=("pv", "sum"),
            vol_sum=("volume", "sum"),
        )
        vwap_data.append(daily)
    combined = pd.concat(vwap_data).groupby(level=[0, 1]).sum()
    combined["vwap"] = combined["pv_sum"] / combined["vol_sum"]
    return combined[["vwap"]]
```

### GroupBy Performance Tips

```python
import pandas as pd
import numpy as np

# Sample multi-stock data
n = 1_000_000
df = pd.DataFrame({
    "symbol": np.random.choice([f"STK_{i:04d}" for i in range(500)], n),
    "date": pd.date_range("2020-01-01", periods=n, freq="T"),
    "price": np.random.randn(n) * 5 + 100,
    "volume": np.random.randint(100, 10_000, n),
})

# TIP 1: sort=False khi không cần result sorted (faster)
result = df.groupby("symbol", sort=False)["price"].mean()

# TIP 2: observed=True cho categorical groupby (tránh compute empty groups)
df["symbol"] = df["symbol"].astype("category")
result = df.groupby("symbol", observed=True)["price"].mean()

# TIP 3: agg với dict thay vì multiple groupby calls
result = df.groupby("symbol").agg(
    mean_price=("price", "mean"),
    vol_price=("price", "std"),
    total_volume=("volume", "sum"),
    n_trades=("price", "count"),
)

# TIP 4: transform để add aggregated values back
# (thay vì merge sau khi groupby)
df["avg_daily_volume"] = df.groupby("symbol")["volume"].transform("mean")

# TIP 5: filter trước groupby để reduce data size
df_filtered = df[df["volume"] > 1000]
result = df_filtered.groupby("symbol")["price"].mean()
```

---

## Phần 5: Memory Optimization

---

### Generators vs Lists

```python
import sys
from typing import Iterator, Generator

# List: tất cả values trong memory
def get_all_returns_list(n_stocks: int, n_days: int) -> list[float]:
    import numpy as np
    return [float(np.random.randn()) for _ in range(n_stocks * n_days)]

# Generator: lazy, O(1) memory
def get_returns_generator(n_stocks: int, n_days: int) -> Generator[float, None, None]:
    import numpy as np
    for _ in range(n_stocks * n_days):
        yield float(np.random.randn())

# Memory comparison
n_stocks, n_days = 1000, 252

list_result = get_all_returns_list(n_stocks, n_days)
gen_result = get_returns_generator(n_stocks, n_days)

print(f"List size: {sys.getsizeof(list_result):,} bytes")   # ~2 MB
print(f"Generator: {sys.getsizeof(gen_result):,} bytes")    # ~112 bytes

# Generator pipeline cho large-scale data processing
def read_ticks(filepath: str) -> Iterator[dict]:
    with open(filepath) as f:
        for line in f:
            parts = line.strip().split(",")
            yield {"symbol": parts[0], "price": float(parts[1]), "volume": int(parts[2])}

def filter_large_trades(ticks: Iterator[dict], min_volume: int = 10_000) -> Iterator[dict]:
    for tick in ticks:
        if tick["volume"] >= min_volume:
            yield tick

def compute_vwap_streaming(ticks: Iterator[dict]) -> dict[str, float]:
    """Compute VWAP without loading all ticks into memory."""
    pv_sums: dict[str, float] = {}
    vol_sums: dict[str, float] = {}
    for tick in ticks:
        sym = tick["symbol"]
        pv_sums[sym] = pv_sums.get(sym, 0.0) + tick["price"] * tick["volume"]
        vol_sums[sym] = vol_sums.get(sym, 0.0) + tick["volume"]
    return {sym: pv_sums[sym] / vol_sums[sym] for sym in pv_sums}

# Sử dụng: memory efficient pipeline
# vwap = compute_vwap_streaming(filter_large_trades(read_ticks("ticks.csv")))
```

### `__slots__` để giảm memory object

```python
import sys

# Regular class: mỗi instance có __dict__ (overhead ~232 bytes)
class PricePoint:
    def __init__(self, symbol: str, price: float, volume: int, timestamp: float):
        self.symbol = symbol
        self.price = price
        self.volume = volume
        self.timestamp = timestamp

# Slotted class: không có __dict__ — tiết kiệm ~30-50% memory
class PricePointSlotted:
    __slots__ = ("symbol", "price", "volume", "timestamp")

    def __init__(self, symbol: str, price: float, volume: int, timestamp: float):
        self.symbol = symbol
        self.price = price
        self.volume = volume
        self.timestamp = timestamp

# Memory comparison (quan trọng khi có hàng triệu tick objects)
regular = PricePoint("AAPL", 150.0, 10000, 1700000000.0)
slotted = PricePointSlotted("AAPL", 150.0, 10000, 1700000000.0)

print(f"Regular (object): {sys.getsizeof(regular)} bytes")
print(f"Regular (__dict__): {sys.getsizeof(regular.__dict__)} bytes")
print(f"Slotted: {sys.getsizeof(slotted)} bytes")
print(f"No __dict__ on slotted: {not hasattr(slotted, '__dict__')}")

# At scale: 10M tick objects
# Regular: ~2.8 GB
# Slotted: ~560 MB — 5x reduction
```

### Memory Profiling

```python
import tracemalloc
import numpy as np

# tracemalloc — built-in, no installation needed
tracemalloc.start()

# Snapshot 1
snapshot1 = tracemalloc.take_snapshot()

# Allocate some memory
data = np.random.randn(1000, 1000)  # ~8MB
result = data @ data.T              # another ~8MB

# Snapshot 2
snapshot2 = tracemalloc.take_snapshot()

# Compare snapshots
stats = snapshot2.compare_to(snapshot1, "lineno")
print("Top 5 memory allocations:")
for stat in stats[:5]:
    print(stat)

tracemalloc.stop()

# memory_profiler — line-by-line (install: pip install memory-profiler)
# from memory_profiler import profile
#
# @profile
# def compute_rolling_correlation(prices: np.ndarray, window: int = 60) -> np.ndarray:
#     n_stocks = prices.shape[1]
#     n_days = prices.shape[0]
#     results = []
#     for i in range(window, n_days):
#         window_data = prices[i-window:i, :]
#         corr = np.corrcoef(window_data.T)
#         results.append(corr)
#     return np.array(results)
```

### numpy memmap — dữ liệu lớn hơn RAM

```python
import numpy as np
import os

# Khi nào dùng memmap:
# - File dữ liệu lớn hơn RAM
# - Cần random access theo rows/cols (không phải sequential)
# - Nhiều processes cần đọc cùng file (shared memory)

# Tạo memmap file (giả lập historical price database)
# 10,000 stocks × 5,000 days × float32 = 200MB — fit in RAM
# 100,000 stocks × 20,000 days × float32 = 8GB — không fit
shape = (20_000, 10_000)  # days × stocks
dtype = np.float32

# Write: tạo memmap file trên disk
fp = np.memmap("/tmp/prices.dat", dtype=dtype, mode="w+", shape=shape)
fp[:100, :] = np.random.randn(100, 10_000).astype(np.float32)
del fp  # flush và close

# Read: load chỉ cần thiết
fp = np.memmap("/tmp/prices.dat", dtype=dtype, mode="r", shape=shape)

# Chỉ load 1 stock's history — OS chỉ page in relevant pages
stock_50_prices = fp[:, 50]   # entire history for stock 50 — OS lazy loading
recent_week = fp[-5:, :]      # last 5 days all stocks

print(f"File size: {os.path.getsize('/tmp/prices.dat') / 1e6:.0f} MB")
print(f"Loaded slice shape: {stock_50_prices.shape}")
```

---

## Phần 6: Python Profiling

---

### Workflow: Profile → Bottleneck → Fix → Verify

```python
import cProfile
import pstats
import io
import numpy as np

# Step 1: cProfile — function-level profiling
def slow_portfolio_backtest(returns: np.ndarray, weights: np.ndarray) -> dict:
    """Simulate a slow backtest."""
    n_days, n_stocks = returns.shape
    portfolio_returns = []

    for day in range(n_days):
        # BAD: Python loop + redundant computation
        day_return = sum(
            returns[day, i] * weights[i]
            for i in range(n_stocks)
        )
        portfolio_returns.append(day_return)

    portfolio_arr = np.array(portfolio_returns)
    sharpe = portfolio_arr.mean() / portfolio_arr.std() * np.sqrt(252)
    return {"returns": portfolio_arr, "sharpe": float(sharpe)}

def fast_portfolio_backtest(returns: np.ndarray, weights: np.ndarray) -> dict:
    """Vectorized version."""
    portfolio_returns = returns @ weights  # matrix multiply — one BLAS call
    sharpe = portfolio_returns.mean() / portfolio_returns.std() * np.sqrt(252)
    return {"returns": portfolio_returns, "sharpe": float(sharpe)}

# Profile slow version
returns = np.random.randn(252, 500)
weights = np.ones(500) / 500

profiler = cProfile.Profile()
profiler.enable()
result = slow_portfolio_backtest(returns, weights)
profiler.disable()

# Print stats
stream = io.StringIO()
stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
stats.print_stats(15)  # top 15 functions
print(stream.getvalue())

# Kết quả sẽ chỉ ra:
# - Bao nhiêu % thời gian trong Python loop
# - Các function nào được gọi nhiều nhất
```

```python
# Step 2: line_profiler — line-by-line (install: pip install line-profiler)
# Chạy: kernprof -l -v script.py
# Hoặc trong Jupyter: %load_ext line_profiler; %lprun -f func func(args)

# Đánh dấu function cần profile:
# @profile  # decorator được inject bởi kernprof
# def compute_factors(prices: np.ndarray) -> np.ndarray:
#     returns = np.diff(prices, axis=0) / prices[:-1, :]      # Line 1
#     momentum = returns[-20:, :].mean(axis=0)                 # Line 2
#     vol = returns[-60:, :].std(axis=0)                       # Line 3
#     quality = momentum / (vol + 1e-8)                        # Line 4
#     return quality

# Output sẽ show:
# Line #   Hits  Time  Per Hit  % Time  Line Contents
# ====================================================
#     1       1   150     150    15.0%  returns = np.diff(...)
#     2       1   200     200    20.0%  momentum = returns[-20:]...
#     3       1   500     500    50.0%  vol = returns[-60:]...   ← BOTTLENECK
#     4       1    50      50     5.0%  quality = momentum / ...
```

```python
# Step 3: tracemalloc — xem memory allocation tại từng dòng
import tracemalloc

def memory_hungry_function(n: int) -> np.ndarray:
    # Line A: allocate large array
    big_array = np.random.randn(n, n)     # n×n float64
    # Line B: another allocation
    result = big_array @ big_array.T       # n×n result
    # Line C: unnecessary copy
    return result.copy()                   # could just return result

tracemalloc.start()
output = memory_hungry_function(1000)
snapshot = tracemalloc.take_snapshot()
tracemalloc.stop()

stats = snapshot.statistics("lineno")
for stat in stats[:5]:
    print(stat)
# Sẽ show: line C allocates 8MB unnecessarily → remove .copy()
```

---

## Phần 7: Caching Patterns

---

### functools.lru_cache và functools.cache

```python
import functools
import time
import numpy as np
from typing import Tuple

# lru_cache — LRU eviction với maxsize
@functools.lru_cache(maxsize=128)
def get_market_calendar(year: int, exchange: str) -> Tuple[str, ...]:
    """Expensive computation — trading days không thay đổi theo năm."""
    print(f"Computing calendar for {year} {exchange}...")
    time.sleep(0.5)  # simulate expensive computation
    # Return tuple (hashable — required for cache key)
    return tuple(f"{year}-01-{d:02d}" for d in range(1, 32))

# functools.cache — unbounded cache (Python 3.9+, no maxsize)
@functools.cache
def compute_beta(symbol: str, benchmark: str, lookback_days: int) -> float:
    """Beta không đổi nhiều — cache 1 ngày là đủ."""
    print(f"Computing beta for {symbol} vs {benchmark}...")
    np.random.seed(hash(symbol) % 1000)
    return float(np.random.randn() * 0.5 + 1.0)

# Demonstrate caching
start = time.perf_counter()
cal1 = get_market_calendar(2024, "NYSE")  # computed
cal2 = get_market_calendar(2024, "NYSE")  # cached!
cal3 = get_market_calendar(2023, "NYSE")  # computed (different key)
elapsed = time.perf_counter() - start
print(f"Total time: {elapsed:.2f}s")  # ~1.0s (2 computes), not 1.5s

# Cache info
print(get_market_calendar.cache_info())  # CacheInfo(hits=1, misses=2, ...)

# LRU cache với custom key (khi args không hashable — e.g. numpy arrays)
def make_hashable(arr: np.ndarray) -> int:
    return hash(arr.tobytes())

_beta_cache: dict[int, float] = {}

def get_cached_correlation(returns_a: np.ndarray, returns_b: np.ndarray) -> float:
    """Custom cache cho numpy arrays."""
    key = make_hashable(returns_a) ^ make_hashable(returns_b)
    if key not in _beta_cache:
        _beta_cache[key] = float(np.corrcoef(returns_a, returns_b)[0, 1])
    return _beta_cache[key]
```

### joblib.Memory — Expensive Computations với Disk Cache

```python
from joblib import Memory
import numpy as np
import time

# Disk-persistent cache — survive process restarts
memory = Memory(location="/tmp/joblib_cache", verbose=0)

@memory.cache
def compute_covariance_matrix(
    symbols: tuple[str, ...],  # tuple for hashability
    start_date: str,
    end_date: str,
    lookback: int = 252,
) -> np.ndarray:
    """
    Covariance matrix computation — takes 30s for 500 stocks.
    Với joblib: chỉ tính 1 lần, sau đó load từ disk.
    """
    print(f"Computing covariance for {len(symbols)} symbols...")
    time.sleep(2)  # simulate expensive computation
    n = len(symbols)
    return np.random.randn(n, n)

# First call: computes and caches to disk
symbols = tuple(f"STK_{i:04d}" for i in range(500))

start = time.perf_counter()
cov1 = compute_covariance_matrix(symbols, "2023-01-01", "2023-12-31")
t1 = time.perf_counter() - start
print(f"First call: {t1:.2f}s")   # ~2s

# Second call: loads from disk
start = time.perf_counter()
cov2 = compute_covariance_matrix(symbols, "2023-01-01", "2023-12-31")
t2 = time.perf_counter() - start
print(f"Cached call: {t2:.4f}s")  # ~0.1s

# Clear cache khi cần recompute
# memory.clear(warn=False)
```

### Khi nào cache useful vs harmful

```
Cache USEFUL khi:
✓ Pure function (same inputs → same output luôn luôn)
✓ Computation expensive (> 100ms)
✓ Same inputs được gọi nhiều lần
✓ Data không thay đổi trong session (historical prices, calendars)
✓ Kết quả nhỏ hơn nhiều so với computation cost

Cache HARMFUL khi:
✗ Function có side effects
✗ Data thay đổi thường xuyên (real-time prices)
✗ Args không hashable → cần convert (overhead có thể > saving)
✗ Cache key space quá lớn → cache miss rate cao, memory waste
✗ Memory-sensitive environments (cache accumulates over time)
✗ Distributed systems (cache không shared giữa workers)
```

---

## Phần 8: Interview Q&A — Python Performance

---

### Q1: "Your quant strategy takes 2 hours to backtest, how do you speed it up?"

**Trả lời mẫu (STAR format):**

Đầu tiên, tôi sẽ **profile trước khi optimize** — đừng đoán mò bottleneck.

**Bước 1: Profile**
```python
import cProfile
profiler = cProfile.Profile()
profiler.enable()
run_backtest(universe, start_date, end_date)
profiler.disable()
profiler.print_stats(sort="cumulative")
```

**Bước 2: Phân tích kết quả theo nguyên tắc 80/20**

Giả sử profile cho thấy:
- 70% time: `compute_signals()` — Python loops trên 1000 stocks
- 20% time: `load_data()` — sequential file reads
- 10% time: `calculate_portfolio()` — có thể chấp nhận

**Bước 3: Fix theo thứ tự impact**

```python
# Fix 1: Vectorize signal computation
# BEFORE: Python loop qua 1000 stocks × 252 days = 252,000 iterations
def compute_signals_slow(prices_dict: dict) -> dict:
    signals = {}
    for symbol, prices in prices_dict.items():
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        momentum = sum(returns[-20:]) / 20
        signals[symbol] = momentum
    return signals

# AFTER: NumPy matrix operations — 200x faster
def compute_signals_fast(prices_matrix: np.ndarray, symbols: list[str]) -> np.ndarray:
    returns = np.diff(prices_matrix, axis=0) / prices_matrix[:-1, :]
    momentum = returns[-20:, :].mean(axis=0)  # single operation
    return momentum

# Fix 2: Parallel data loading
from concurrent.futures import ThreadPoolExecutor

def load_all_data_parallel(symbols: list[str], start: str, end: str) -> dict:
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {sym: executor.submit(load_data, sym, start, end) for sym in symbols}
        return {sym: fut.result() for sym, fut in futures.items()}

# Fix 3: Parallelize across parameter sets
from concurrent.futures import ProcessPoolExecutor

def parallel_parameter_sweep(param_grid: list[dict]) -> list[dict]:
    with ProcessPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(run_single_backtest, param_grid))
    return results
```

**Kết quả điển hình:**
- Vectorization: 2 hours → 3 minutes (40x)
- Parallel loading: 3 minutes → 30 seconds (6x)
- Parallel parameter sweep: linear với số cores

---

### Q2: "You have 500M rows of tick data to process, what's your approach?"

**Trả lời:**

500M rows ticks ~ 50-100GB CSV. Approach:

**1. Storage Layer trước tiên:**
```
Parquet (columnar) + Snappy compression:
- 100GB CSV → ~15GB Parquet (7x compression)
- Read specific columns: 100x faster than CSV
- Partitioned by date: skip days không cần thiết
```

**2. Processing với Dask hoặc chunked Pandas:**
```python
import dask.dataframe as dd

# Dask: lazy computation, parallel, out-of-core
df = dd.read_parquet(
    "s3://bucket/ticks/",
    columns=["symbol", "price", "volume", "timestamp"],
)

# Filter + compute — only executed when .compute() called
result = (
    df[df["volume"] > 10_000]
    .groupby(["symbol", df["timestamp"].dt.date])
    .agg({"price": ["mean", "std"], "volume": "sum"})
    .compute()  # triggers actual computation, parallel
)
```

**3. Schema optimization:**
```python
dtypes = {
    "symbol": "category",    # 10K symbols → saves 90% vs string
    "price": "float32",       # 4 bytes vs 8 bytes
    "volume": "int32",        # 4 bytes vs 8 bytes
    "exchange": "category",
}
# 500M rows:
# float64 columns: 500M × 8B = 4GB per column
# float32 columns: 500M × 4B = 2GB per column
```

**4. Validate kết quả trên sample trước:**
```python
# Test trên 1 ngày (~ 1M rows)
# Verify logic đúng
# Scale lên toàn bộ
```

---

### Q3: "Explain the difference between threading and multiprocessing in Python"

**Trả lời ngắn gọn:**

```
Threading (threading module):
- Threads chia sẻ cùng memory space
- GIL cho phép chỉ 1 thread chạy Python bytecode tại mỗi thời điểm
- NHƯNG GIL được release khi: I/O, C extensions (numpy)
- → Tốt cho: I/O-bound (API calls, DB queries, file I/O)
- → Không tốt cho: CPU-bound pure Python code
- Overhead thấp: thread creation nhanh, no serialization

Multiprocessing (multiprocessing module):
- Mỗi process: Python interpreter riêng → không GIL
- Memory riêng → phải serialize data giữa processes (pickle)
- → Tốt cho: CPU-bound (heavy computation, pure Python algorithms)
- → Overhead cao: process creation, pickling data
- Không share memory → cần mp.Queue, mp.Pipe, mp.Manager để communicate

Rule of thumb:
- API calls, web scraping, DB I/O → threading (hoặc asyncio)
- Heavy Python computation, image processing → multiprocessing
- NumPy heavy computation → threading có thể OK (GIL released in C)
```

---

### Q4: "How would you parallelize a backtest across 1000 stocks?"

**Trả lời:**

```python
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from dataclasses import dataclass
from typing import NamedTuple

class BacktestResult(NamedTuple):
    symbol: str
    sharpe: float
    total_return: float
    max_drawdown: float

def backtest_single_stock(args: tuple[str, np.ndarray, dict]) -> BacktestResult:
    """
    Chạy trong separate process — không share memory với main.
    Args phải serializable (pickle) → dùng numpy arrays, primitive types.
    """
    symbol, prices, params = args

    # Signal generation
    returns = np.diff(prices) / prices[:-1]
    ma_short = np.convolve(prices, np.ones(params["short"]) / params["short"], "valid")
    ma_long  = np.convolve(prices, np.ones(params["long"])  / params["long"],  "valid")

    # Align lengths
    min_len = min(len(ma_short), len(ma_long))
    signal = np.sign(ma_short[-min_len:] - ma_long[-min_len:])

    # Portfolio simulation
    strategy_returns = returns[-min_len:] * signal[:-1] if min_len > 1 else returns[:1]

    sharpe = strategy_returns.mean() / (strategy_returns.std() + 1e-8) * np.sqrt(252)
    total_return = float(np.prod(1 + strategy_returns) - 1)

    # Max drawdown
    cumulative = np.cumprod(1 + strategy_returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    max_dd = float(drawdown.min())

    return BacktestResult(
        symbol=symbol,
        sharpe=float(sharpe),
        total_return=total_return,
        max_drawdown=max_dd,
    )

def parallel_backtest_universe(
    price_data: dict[str, np.ndarray],
    params: dict,
    n_workers: int = mp.cpu_count(),
) -> list[BacktestResult]:
    """
    Backtest 1000 stocks in parallel.
    n_workers = CPU count (CPU-bound task).
    """
    args_list = [(sym, prices, params) for sym, prices in price_data.items()]

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        results = list(executor.map(
            backtest_single_stock,
            args_list,
            chunksize=10,  # batch args để reduce IPC overhead
        ))

    return sorted(results, key=lambda r: r.sharpe, reverse=True)

# Usage
if __name__ == "__main__":  # Required for multiprocessing on Windows/macOS
    symbols = [f"STK_{i:04d}" for i in range(1000)]
    price_data = {sym: np.random.randn(252).cumsum() + 100 for sym in symbols}
    params = {"short": 10, "long": 50}

    results = parallel_backtest_universe(price_data, params)
    print(f"Best strategy: {results[0].symbol} Sharpe={results[0].sharpe:.2f}")

# Time estimates:
# Sequential (1000 stocks):  ~60s
# Parallel (8 cores):        ~8s  (7.5x speedup)
# Note: linear scaling limited by pickle overhead and IPC
```

---

*Tổng hợp: Module 02 bao gồm GIL mechanics, concurrency models với code templates thực tế, NumPy vectorization với benchmarks, Pandas performance patterns, memory optimization, và 4 interview Q&A chuẩn WorldQuant-level.*
