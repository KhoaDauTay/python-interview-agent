# OOP & Python Deep Dive — WorldQuant Interview

> WQ criteria: "Python, OOP, Time complexity" + "walk through past projects with technical depth"
> Focus: Python-idiomatic OOP, SOLID, design patterns interviewer thực sự hỏi, và cách kể chuyện dự án.

---

## 1. OOP Fundamentals — 4 Pillars + Python cụ thể

### Encapsulation

Gom data + behavior vào một unit; ẩn implementation details.

```python
class Portfolio:
    def __init__(self, name: str):
        self.name = name
        self._positions: dict[str, float] = {}   # _ = convention "private"
        self.__nav: float = 0.0                   # __ = name mangling (_Portfolio__nav)

    def add_position(self, symbol: str, value: float) -> None:
        if value < 0:
            raise ValueError("Position value cannot be negative")
        self._positions[symbol] = value
        self.__nav += value

    @property
    def nav(self) -> float:
        """Read-only public interface to private __nav."""
        return self.__nav

    @property
    def positions(self) -> dict[str, float]:
        return self._positions.copy()  # Return copy, not reference (protect internal state)

p = Portfolio("Alpha Fund")
p.add_position("AAPL", 1_000_000)
print(p.nav)              # 1000000.0 — via property
print(p._Portfolio__nav)  # Access mangled name (possible but bad practice)
```

**Interview point:** `_x` = "internal use", `__x` = name mangling (prevents accidental override in subclasses). `@property` = controlled access, can add validation/computation.

---

### Inheritance

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Abstract base — defines interface
class DataSource(ABC):
    @abstractmethod
    def fetch(self, symbol: str, start: str, end: str) -> list[dict]:
        """Fetch OHLCV data for symbol."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...

    # Concrete method shared by all subclasses
    def fetch_safe(self, symbol: str, start: str, end: str) -> list[dict]:
        if not self.is_available():
            raise RuntimeError(f"{self.__class__.__name__} not available")
        return self.fetch(symbol, start, end)

# Concrete implementations
class BloombergSource(DataSource):
    def __init__(self, api_key: str):
        self._client = BloombergAPI(api_key)

    def fetch(self, symbol: str, start: str, end: str) -> list[dict]:
        return self._client.get_historical(symbol, start, end)

    def is_available(self) -> bool:
        return self._client.ping()

class CSVSource(DataSource):
    def __init__(self, data_dir: str):
        self._dir = data_dir

    def fetch(self, symbol: str, start: str, end: str) -> list[dict]:
        import pandas as pd
        df = pd.read_csv(f"{self._dir}/{symbol}.csv")
        return df[df["date"].between(start, end)].to_dict("records")

    def is_available(self) -> bool:
        import os
        return os.path.isdir(self._dir)

# Usage: same interface, swap implementation
def run_backtest(source: DataSource, symbols: list[str]) -> dict:
    for symbol in symbols:
        data = source.fetch_safe(symbol, "2020-01-01", "2024-12-31")
        # ... process
```

**Interview point:** ABC enforces contract — `TypeError` at instantiation if `@abstractmethod` not implemented. Prefer composition over deep inheritance hierarchies (>2 levels = smell).

---

### Polymorphism

Same interface, different behavior. Two forms in Python:

```python
# 1. Subtype polymorphism (via inheritance above)

# 2. Duck typing — Python's preferred form
class SignalEngine:
    def compute(self, prices) -> float:
        return prices[-1] / prices[-20] - 1  # Momentum

class MeanReversion:
    def compute(self, prices) -> float:
        return -(prices[-1] - prices[-5:].mean()) / prices[-5:].std()

class MLModel:
    def compute(self, prices) -> float:
        return self.model.predict(prices[-60:].reshape(1, -1))[0]

def generate_signals(strategy, all_prices: dict) -> dict:
    # strategy can be ANY object with .compute() method — no ABC needed
    return {sym: strategy.compute(prices) for sym, prices in all_prices.items()}

# All work — Python doesn't care about type, only behavior
generate_signals(SignalEngine(), prices)
generate_signals(MeanReversion(), prices)
generate_signals(MLModel(), prices)

# For type hints with duck typing: use Protocol
from typing import Protocol
import numpy as np

class Computable(Protocol):
    def compute(self, prices: np.ndarray) -> float: ...

def generate_signals(strategy: Computable, all_prices: dict) -> dict:
    # Type checker knows strategy must have .compute()
    return {sym: strategy.compute(prices) for sym, prices in all_prices.items()}
```

---

### Abstraction

Hide complexity behind simple interface.

```python
class BacktestEngine:
    """
    Hides: data loading, signal computation, trade simulation, cost modeling.
    Exposes: simple run() interface.
    """
    def __init__(self, data_source: DataSource, strategy, cost_model):
        self._data = data_source
        self._strategy = strategy
        self._cost = cost_model

    def run(self, symbols: list[str], start: str, end: str) -> "BacktestResult":
        prices = self._load_prices(symbols, start, end)      # Hidden
        signals = self._compute_signals(prices)               # Hidden
        trades = self._simulate_trades(signals, prices)       # Hidden
        return BacktestResult(trades, self._cost)             # Hidden

    def _load_prices(self, symbols, start, end): ...
    def _compute_signals(self, prices): ...
    def _simulate_trades(self, signals, prices): ...

# Researcher uses:
engine = BacktestEngine(CSVSource("/data"), MomentumStrategy(), LinearCostModel())
result = engine.run(["AAPL", "MSFT"], "2020-01-01", "2024-12-31")
# They don't know OR care about internal complexity
```

---

## 2. Python OOP — Dunder Methods (Interviewer loves these)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterator

@dataclass
class Position:
    symbol: str
    shares: float
    price: float

    @property
    def value(self) -> float:
        return self.shares * self.price

    def __repr__(self) -> str:
        return f"Position({self.symbol}, {self.shares}@{self.price})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Position):
            return NotImplemented
        return self.symbol == other.symbol

    def __hash__(self) -> int:
        return hash(self.symbol)  # Required when defining __eq__

    def __lt__(self, other: Position) -> bool:
        return self.value < other.value    # Enable sorting by value

    def __add__(self, other: Position) -> Position:
        if self.symbol != other.symbol:
            raise ValueError("Cannot add positions of different symbols")
        return Position(self.symbol, self.shares + other.shares, self.price)


class Portfolio:
    def __init__(self, name: str):
        self.name = name
        self._positions: list[Position] = []

    def add(self, pos: Position) -> None:
        self._positions.append(pos)

    def __len__(self) -> int:
        return len(self._positions)

    def __getitem__(self, idx: int) -> Position:
        return self._positions[idx]

    def __iter__(self) -> Iterator[Position]:
        return iter(self._positions)

    def __contains__(self, symbol: str) -> bool:
        return any(p.symbol == symbol for p in self._positions)

    def __repr__(self) -> str:
        return f"Portfolio('{self.name}', {len(self)} positions)"

    def __bool__(self) -> bool:
        return len(self._positions) > 0

    # Context manager — for resource management
    def __enter__(self) -> Portfolio:
        print(f"Opening portfolio: {self.name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        print(f"Closing portfolio: {self.name}")
        return False  # Don't suppress exceptions

# Usage
p = Portfolio("Quant Fund A")
p.add(Position("AAPL", 100, 185.0))
p.add(Position("MSFT", 200, 420.0))

print(len(p))           # __len__: 2
print(p[0])             # __getitem__: Position(AAPL, 100@185.0)
print("AAPL" in p)      # __contains__: True
for pos in p:           # __iter__
    print(pos)
print(bool(p))          # __bool__: True

with Portfolio("Temp") as temp_p:   # __enter__/__exit__
    temp_p.add(Position("GOOG", 50, 180.0))
```

**Key dunders by use case:**
```
Representation:   __repr__ (unambiguous), __str__ (human-readable)
Comparison:       __eq__, __lt__, __le__, __gt__, __ge__ (+ functools.total_ordering)
Arithmetic:       __add__, __sub__, __mul__, __truediv__, __radd__ (reflected)
Container:        __len__, __getitem__, __setitem__, __contains__, __iter__
Context manager:  __enter__, __exit__
Callable:         __call__ (makes instance callable like a function)
Hashing:          __hash__ (define when defining __eq__)
```

---

## 3. Properties & Descriptors

```python
class DataCache:
    def __init__(self):
        self._data = {}
        self._max_size = 1000

    @property
    def max_size(self) -> int:
        return self._max_size

    @max_size.setter
    def max_size(self, value: int) -> None:
        if value < 1:
            raise ValueError("max_size must be >= 1")
        if value < len(self._data):
            # Evict excess entries
            excess = len(self._data) - value
            keys_to_remove = list(self._data.keys())[:excess]
            for k in keys_to_remove:
                del self._data[k]
        self._max_size = value

    @property
    def size(self) -> int:
        return len(self._data)  # Read-only computed property

# Descriptor — reusable property logic across classes
class ValidatedFloat:
    """Descriptor: validates float >= 0. Reusable across any class."""

    def __set_name__(self, owner, name: str) -> None:
        self._name = f"_{name}"  # Store as _price, _volume, etc.

    def __get__(self, obj, objtype=None) -> float:
        if obj is None:
            return self  # Access via class, not instance
        return getattr(obj, self._name, 0.0)

    def __set__(self, obj, value: float) -> None:
        if not isinstance(value, (int, float)):
            raise TypeError(f"{self._name} must be numeric")
        if value < 0:
            raise ValueError(f"{self._name} cannot be negative")
        setattr(obj, self._name, float(value))

class Trade:
    price = ValidatedFloat()   # Descriptor instance
    quantity = ValidatedFloat()

    def __init__(self, symbol: str, price: float, quantity: float):
        self.symbol = symbol
        self.price = price         # Goes through ValidatedFloat.__set__
        self.quantity = quantity   # Goes through ValidatedFloat.__set__

t = Trade("AAPL", 185.0, 100)
# t.price = -10  → ValueError: _price cannot be negative
```

---

## 4. SOLID Principles — Python Examples

### S — Single Responsibility

```python
# ❌ BAD: One class does everything
class DataProcessor:
    def fetch_data(self): ...       # Data access
    def validate_data(self): ...    # Validation
    def compute_signal(self): ...   # Business logic
    def save_to_db(self): ...       # Persistence
    def send_alert(self): ...       # Notification
    # One change ripples through everything

# ✅ GOOD: Each class has one reason to change
class MarketDataFetcher:
    def fetch(self, symbol: str) -> pd.DataFrame: ...

class DataValidator:
    def validate(self, df: pd.DataFrame) -> tuple[bool, list[str]]: ...

class SignalComputer:
    def compute(self, df: pd.DataFrame) -> pd.Series: ...

class SignalRepository:
    def save(self, signals: pd.Series) -> None: ...
```

### O — Open/Closed

```python
# Open for extension, closed for modification

# ❌ BAD: Add new signal type → must modify existing class
class SignalGenerator:
    def generate(self, type: str, prices):
        if type == "momentum":
            return prices.pct_change(20)
        elif type == "mean_reversion":
            return -(prices - prices.rolling(20).mean())
        elif type == "NEW_TYPE":      # ← Must modify this class every time
            ...

# ✅ GOOD: Add new type by extension, not modification
from abc import ABC, abstractmethod

class Signal(ABC):
    @abstractmethod
    def compute(self, prices: pd.Series) -> pd.Series: ...

class MomentumSignal(Signal):
    def __init__(self, window: int = 20):
        self.window = window
    def compute(self, prices: pd.Series) -> pd.Series:
        return prices.pct_change(self.window)

class MeanReversionSignal(Signal):
    def __init__(self, window: int = 20):
        self.window = window
    def compute(self, prices: pd.Series) -> pd.Series:
        return -(prices - prices.rolling(self.window).mean())

# Add new type: create new class, touch nothing existing
class VolatilitySignal(Signal):
    def compute(self, prices: pd.Series) -> pd.Series:
        return -prices.pct_change().rolling(20).std()  # New, no existing code changed
```

### L — Liskov Substitution

```python
# Subclass must be usable wherever parent is used, without breaking behavior

# ❌ VIOLATES LSP: Square inherits Rectangle but breaks invariant
class Rectangle:
    def __init__(self, w: float, h: float):
        self.width = w
        self.height = h

    def area(self) -> float:
        return self.width * self.height

class Square(Rectangle):
    def __init__(self, side: float):
        super().__init__(side, side)

    # Violation: setting width must also set height to maintain square
    @Rectangle.width.setter
    def width(self, value):
        self._width = value
        self._height = value  # Side effect breaks Rectangle contract

# Code expecting Rectangle breaks with Square:
def double_width(r: Rectangle):
    r.width *= 2
    assert r.area() == r.width * r.height  # FAILS for Square

# ✅ FIX: Don't inherit, use separate hierarchy or composition
class Shape(ABC):
    @abstractmethod
    def area(self) -> float: ...

class Rectangle(Shape):
    def __init__(self, w: float, h: float):
        self.width, self.height = w, h
    def area(self) -> float:
        return self.width * self.height

class Square(Shape):  # Sibling, not child
    def __init__(self, side: float):
        self.side = side
    def area(self) -> float:
        return self.side ** 2
```

### I — Interface Segregation

```python
# ❌ BAD: Fat interface forces implementation of unneeded methods
class DataStore(ABC):
    @abstractmethod
    def read(self): ...
    @abstractmethod
    def write(self): ...
    @abstractmethod
    def delete(self): ...
    @abstractmethod
    def search(self): ...       # CSV store can't do this efficiently
    @abstractmethod
    def stream(self): ...       # Most stores don't support streaming

# ✅ GOOD: Small, focused interfaces
class Readable(Protocol):
    def read(self, key: str) -> dict: ...

class Writable(Protocol):
    def write(self, key: str, data: dict) -> None: ...

class Searchable(Protocol):
    def search(self, query: str) -> list[dict]: ...

class CSVStore:  # Only implements what it can
    def read(self, key: str) -> dict: ...
    def write(self, key: str, data: dict) -> None: ...
    # No search — CSV isn't good at this, don't force it

class ElasticsearchStore:
    def read(self, key: str) -> dict: ...
    def write(self, key: str, data: dict) -> None: ...
    def search(self, query: str) -> list[dict]: ...
```

### D — Dependency Inversion

```python
# High-level modules should not depend on low-level modules
# Both should depend on abstractions

# ❌ BAD: BacktestEngine directly depends on specific implementation
class BacktestEngine:
    def __init__(self):
        self.db = PostgreSQLDatabase()  # Hardcoded concrete class

# ✅ GOOD: Depend on abstraction, inject concrete implementation
class Database(Protocol):
    def save_result(self, result: dict) -> None: ...
    def load_result(self, id: str) -> dict: ...

class BacktestEngine:
    def __init__(self, db: Database):    # Depends on abstraction
        self._db = db

    def run(self, ...) -> None:
        result = self._compute()
        self._db.save_result(result)     # Works with ANY Database implementation

# Production
engine = BacktestEngine(PostgreSQLDatabase())
# Testing
engine = BacktestEngine(InMemoryDatabase())  # No real DB needed for tests
```

---

## 5. Design Patterns — Những cái hay bị hỏi

### Strategy Pattern

```python
# Swap algorithm at runtime without changing client code
from abc import ABC, abstractmethod

class RebalanceStrategy(ABC):
    @abstractmethod
    def rebalance(self, portfolio: dict, target: dict) -> list[dict]:
        """Returns list of trades to execute."""
        ...

class EqualWeightStrategy(RebalanceStrategy):
    def rebalance(self, portfolio: dict, target: dict) -> list[dict]:
        n = len(target)
        equal_weight = 1.0 / n
        trades = []
        for symbol, current_weight in portfolio.items():
            diff = equal_weight - current_weight
            if abs(diff) > 0.01:  # 1% threshold
                trades.append({"symbol": symbol, "delta_weight": diff})
        return trades

class MinVarianceStrategy(RebalanceStrategy):
    def rebalance(self, portfolio: dict, target: dict) -> list[dict]:
        # Optimize for minimum portfolio variance
        ...

class PortfolioManager:
    def __init__(self, strategy: RebalanceStrategy):
        self._strategy = strategy

    def set_strategy(self, strategy: RebalanceStrategy) -> None:
        self._strategy = strategy  # Swap at runtime

    def rebalance(self, portfolio: dict, target: dict) -> list[dict]:
        return self._strategy.rebalance(portfolio, target)
```

### Observer Pattern

```python
# Event system: decoupled publish/subscribe
from typing import Callable

class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, handler: Callable) -> None:
        self._subscribers.setdefault(event, []).append(handler)

    def publish(self, event: str, data: dict) -> None:
        for handler in self._subscribers.get(event, []):
            handler(data)

# Usage in quant system
bus = EventBus()

def on_signal(data: dict):
    print(f"Signal generated: {data}")

def on_signal_risk_check(data: dict):
    if abs(data["weight"]) > 0.1:
        print(f"Warning: large weight {data['weight']}")

bus.subscribe("signal_generated", on_signal)
bus.subscribe("signal_generated", on_signal_risk_check)

# When signal is computed:
bus.publish("signal_generated", {"symbol": "AAPL", "weight": 0.05})
# Both handlers called automatically
```

### Factory Pattern

```python
class DataSourceFactory:
    _registry: dict[str, type] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(source_class):
            cls._registry[name] = source_class
            return source_class
        return decorator

    @classmethod
    def create(cls, name: str, **kwargs) -> DataSource:
        if name not in cls._registry:
            raise ValueError(f"Unknown source: {name}. Available: {list(cls._registry)}")
        return cls._registry[name](**kwargs)

@DataSourceFactory.register("bloomberg")
class BloombergSource(DataSource): ...

@DataSourceFactory.register("csv")
class CSVSource(DataSource): ...

# Usage: create by name (from config file, env var, etc.)
source = DataSourceFactory.create("bloomberg", api_key="xxx")
source = DataSourceFactory.create("csv", data_dir="/data")
```

### Decorator Pattern (không phải Python decorator syntax)

```python
# Wrap object to add behavior without inheritance
class CachedDataSource(DataSource):
    """Adds caching to any DataSource without modifying it."""

    def __init__(self, wrapped: DataSource, cache_ttl: int = 3600):
        self._wrapped = wrapped
        self._cache: dict[str, tuple] = {}
        self._ttl = cache_ttl

    def fetch(self, symbol: str, start: str, end: str) -> list[dict]:
        key = f"{symbol}:{start}:{end}"
        cached, timestamp = self._cache.get(key, (None, 0))
        if cached and (time.time() - timestamp) < self._ttl:
            return cached

        result = self._wrapped.fetch(symbol, start, end)
        self._cache[key] = (result, time.time())
        return result

    def is_available(self) -> bool:
        return self._wrapped.is_available()

# Wrap any source with caching — no modification to original
bloomberg = BloombergSource(api_key="xxx")
cached_bloomberg = CachedDataSource(bloomberg, cache_ttl=86400)
```

---

## 6. Walk Through Past Projects — Framework

> WQ criterion: "walk through past projects with technical depth"

### Cấu trúc trả lời (8-10 phút)

```
1. Context (30s):   "The project was X at company Y, solving problem Z."
2. Problem (1min):  "The challenge was specifically [technical detail]."
3. My role (30s):   "I was responsible for [specific component]."
4. Approach (3min): "I decided to use A because B. I considered C but rejected
                     it because D." ← THIS is technical depth
5. Result (1min):   "Outcome: [metric]. Latency went from X to Y."
6. Lessons (1min):  "What I'd do differently: [honest reflection]."
```

### Chuẩn bị 3 projects — template fill-in

**Project template (fill before interview):**

```
Project: [Name]
Company: [Company], [Year]
Scale: [How big: rows/users/QPS/TB of data]
My role: [What I owned specifically]

THE PROBLEM:
  "We had [specific technical pain]: [symptom] because [root cause]."
  Example: "Our data pipeline was taking 6 hours because we were loading
            the entire 200GB dataset into memory, then filtering."

MY APPROACH:
  Option A: [What I chose] → because [technical reason]
  Option B: [What I rejected] → because [specific drawback]
  Key technical decision: [The non-obvious choice you made]

IMPLEMENTATION DEPTH:
  - Data structures used: [e.g., "Used a heap for top-K, not sort, because..."]
  - Algorithm: [e.g., "Sliding window O(n) instead of nested loop O(n²)"]
  - Concurrency: [e.g., "ProcessPoolExecutor because CPU-bound, not threading"]
  - Performance: [e.g., "Reduced memory from 200GB to 8GB using chunked Parquet"]

RESULT:
  - [Metric before] → [metric after]
  - e.g., "Pipeline: 6h → 45min. Memory: 200GB → 8GB."

WHAT I'D DO DIFFERENTLY:
  - [Honest technical reflection — shows maturity]
  - e.g., "I'd use Dask from the start instead of migrating later."
```

### Follow-up questions WQ sẽ hỏi về projects

```
"Why did you choose X over Y?"
→ "I considered Y, but [specific technical reason it didn't fit].
   X was better because [data volume / latency requirement / team familiarity]."

"What was the hardest bug you encountered?"
→ Describe a real bug with technical detail: race condition, off-by-one in
   time-series, look-ahead bias in backtest, memory leak.

"How would you scale this to 10x the data?"
→ Have a ready answer: "The current bottleneck would be X. I'd address it by Y."

"What did you learn?"
→ Technical lesson: "I learned that [Python threading doesn't help CPU-bound code],
   which changed how I think about [parallelism] going forward."
```

---

## 7. Coding Interview — Handle Follow-ups

> WQ: "Solves coding questions (and follow-ups) clearly, efficiently, with minimal bugs"

### Follow-up pattern và cách handle

```
Common follow-up patterns:
1. "Now do it in O(n) instead of O(n log n)"
2. "What if the data doesn't fit in memory?"
3. "What if multiple threads call this simultaneously?"
4. "What if values can be negative / null / duplicate?"
5. "How would you test this?"
```

**Template khi bị follow-up:**

```
Step 1: Repeat the constraint change:
  "So now I need O(n) time — let me think about what data structures give O(1) lookup..."

Step 2: Think aloud about the trade-off:
  "The current approach uses sort (O(n log n)). To get O(n),
   I could use a hash map since lookup is O(1)..."

Step 3: Code the change incrementally:
  Don't rewrite from scratch — modify existing solution and explain why.

Step 4: Update complexity analysis:
  "This changes time from O(n log n) to O(n), space from O(1) to O(n)."
```

**Example: Two Sum follow-ups**

```python
# Original: Two Sum — O(n) time, O(n) space
def two_sum(nums: list[int], target: int) -> list[int]:
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []

# Follow-up 1: "What if the array is sorted? Can you do O(1) space?"
def two_sum_sorted(nums: list[int], target: int) -> list[int]:
    # Two pointer — sorted array allows this O(n) time, O(1) space
    left, right = 0, len(nums) - 1
    while left < right:
        total = nums[left] + nums[right]
        if total == target:
            return [left, right]
        elif total < target:
            left += 1
        else:
            right -= 1
    return []

# Follow-up 2: "What if you need ALL pairs that sum to target?"
def two_sum_all_pairs(nums: list[int], target: int) -> list[list[int]]:
    from collections import defaultdict
    count = defaultdict(list)
    for i, num in enumerate(nums):
        count[num].append(i)

    seen_pairs = set()
    result = []
    for num, indices in count.items():
        complement = target - num
        if complement in count and (min(num, complement), max(num, complement)) not in seen_pairs:
            for i in indices:
                for j in count[complement]:
                    if i != j:
                        result.append([i, j])
            seen_pairs.add((min(num, complement), max(num, complement)))
    return result

# Follow-up 3: "What if nums is a stream (can't store all)? Memory limited."
# → Answer: "With unlimited precision floats in a stream, exact O(1) space isn't possible.
#   I'd use a probabilistic approach (Bloom filter for the seen set) if false positives
#   are acceptable. Or if we can bound value range, use a bit array."
```

---

## 8. Time Complexity — What WQ Expects

### Phân tích complexity như professional

```
Bad answer: "It's O(n²) because there are two loops."

Good answer: "The outer loop runs n times. For each iteration, the inner
operation is O(log n) because we're doing binary search on a sorted
structure. Total: O(n log n). Space is O(n) for the auxiliary storage.
In the average case this is better, but worst case [explain worst case]."
```

### Common patterns + complexity

```python
# Pattern: Sliding Window
def max_subarray_size_k(arr: list[int], k: int) -> int:
    window_sum = sum(arr[:k])
    max_sum = window_sum
    for i in range(k, len(arr)):
        window_sum += arr[i] - arr[i - k]
        max_sum = max(max_sum, window_sum)
    return max_sum
# Time: O(n) — each element added and removed once
# Space: O(1) — no extra storage

# Pattern: Two Pointer
def remove_duplicates(nums: list[int]) -> int:
    if not nums: return 0
    slow = 0
    for fast in range(1, len(nums)):
        if nums[fast] != nums[slow]:
            slow += 1
            nums[slow] = nums[fast]
    return slow + 1
# Time: O(n) — fast pointer traverses once
# Space: O(1) — in-place

# Pattern: BFS (queue-based)
from collections import deque
def level_order(root) -> list[list[int]]:
    if not root: return []
    result, queue = [], deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):   # Process exactly one level
            node = queue.popleft()
            level.append(node.val)
            if node.left: queue.append(node.left)
            if node.right: queue.append(node.right)
        result.append(level)
    return result
# Time: O(n) — each node processed once
# Space: O(w) where w = max width of tree (worst case O(n) for complete tree)

# Pattern: DP
def longest_common_subsequence(s1: str, s2: str) -> int:
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[m][n]
# Time: O(m×n) — fill entire m×n table
# Space: O(m×n) — can optimize to O(min(m,n)) with rolling array
```

### Amortized Analysis — WQ loves this

```python
class DynamicArray:
    """Demonstrate amortized O(1) append."""
    def __init__(self):
        self._data = [None]
        self._size = 0
        self._capacity = 1

    def append(self, val) -> None:
        if self._size == self._capacity:
            self._resize()           # O(n) but rare
        self._data[self._size] = val
        self._size += 1

    def _resize(self) -> None:
        self._capacity *= 2          # Double capacity
        new_data = [None] * self._capacity
        for i in range(self._size):
            new_data[i] = self._data[i]
        self._data = new_data

# Why append is O(1) amortized:
# n appends: resizes at 1, 2, 4, 8, ..., n → copies: 1+2+4+...+n = 2n total copies
# Total work for n appends = n (appends) + 2n (copies) = 3n = O(n)
# Per append: O(n)/n = O(1) amortized
```

---

## Quick Reference

```
4 OOP PILLARS
══════════════════════════════════════════════════════════
Encapsulation:  Hide state, expose interface (@property, _private)
Inheritance:    Reuse + specialize (ABC for contracts, max 2 levels)
Polymorphism:   Same interface, different behavior (duck typing in Python)
Abstraction:    Hide complexity behind simple API

PYTHON DUNDER CHEATSHEET
══════════════════════════════════════════════════════════
__repr__        Unambiguous string representation (for debugging)
__str__         Human-readable (print())
__len__         len(obj)
__getitem__     obj[key]  → makes class subscriptable
__iter__        for x in obj
__contains__    x in obj
__eq__+__hash__ Required together (eq without hash → unhashable)
__enter/exit__  with obj as x: (context manager)
__call__        obj() makes instance callable

SOLID — ONE-LINE EACH
══════════════════════════════════════════════════════════
S: One class, one reason to change
O: Extend by adding, not modifying existing code
L: Subclass usable wherever parent is (don't strengthen preconditions)
I: Many small interfaces > one fat interface
D: Depend on abstractions, inject concrete implementations

COMPLEXITY COMMUNICATION
══════════════════════════════════════════════════════════
Always state: time + space + worst vs average
Amortized: total work / n operations
Say: "This is O(n log n) because [specific reason], 
      but if [constraint], we can get O(n) by [approach]."
══════════════════════════════════════════════════════════
```
