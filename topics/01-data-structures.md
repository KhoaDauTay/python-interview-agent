# Data Structures — Question Bank
> CV context: Khoa đã dùng dict/hashmap (ETL dedup), OrderedDict (LRU-style cache), Linked List (LRU internal), Heap (priority job queue Celery).

---

## EASY

### DS-E01: Array vs Linked List
**Câu hỏi:** Sự khác biệt giữa Array và Linked List là gì? Khi nào nên dùng cái nào?
**Keywords:** random access, O(1) lookup, O(n) insert, memory contiguous
**Follow-up:** "Doubly linked list giải quyết vấn đề gì mà singly linked list không làm được?"

### DS-E02: Stack và Queue
**Câu hỏi:** Mô tả Stack và Queue. Cho ví dụ use-case thực tế của từng loại.
**Keywords:** LIFO, FIFO, call stack, BFS, DFS, `collections.deque`
**Follow-up:** "Dùng gì để implement một Queue hiệu quả trong Python? `list` vs `deque` khác gì?"

### DS-E03: Hash Table cơ bản
**Câu hỏi:** Hash table hoạt động như thế nào? Collision xảy ra khi nào và xử lý thế nào?
**Keywords:** hash function, collision, chaining, open addressing, load factor
**Follow-up:** "Python dict có phải là hash table không? Nó handle collision thế nào?"

---

## MEDIUM

### DS-M01: Design Linked List *(LeetCode 707)*
**Câu hỏi:** Implement một Linked List với các operation: `get(index)`, `addAtHead`, `addAtTail`, `addAtIndex`, `deleteAtIndex`. Time complexity mỗi operation?
**Keywords:** Node class, head pointer, O(n) traversal, index boundary check
**Follow-up:** "Doubly linked list sẽ tối ưu operation nào? Trade-off là gì?"
**Code skeleton:**
```python
class Node:
    def __init__(self, val=0):
        self.val = val
        self.next = None

class MyLinkedList:
    def __init__(self):
        self.head = None
        self.size = 0
```

### DS-M02: Design Hit Counter *(LeetCode 362)*
**Câu hỏi:** Design một hit counter đếm số hits trong 5 phút gần nhất. `hit(timestamp)` và `getHits(timestamp)`.
**Keywords:** sliding window, deque, circular buffer (300 buckets), timestamp modulo
**Expected answer:** Dùng `deque` loại bỏ entries cũ hơn 300 giây
**Follow-up:** "Nếu hệ thống distributed (nhiều server), bạn sẽ design thế nào?"
```python
from collections import deque
class HitCounter:
    def __init__(self):
        self.hits = deque()  # store (timestamp, count)
```

### DS-M03: Time Based Key-Value Store *(LeetCode 981)*
**Câu hỏi:** Design một key-value store hỗ trợ `set(key, value, timestamp)` và `get(key, timestamp)` — trả về value với timestamp lớn nhất ≤ timestamp được hỏi.
**Keywords:** dict of sorted list, binary search, `bisect_right`
**Expected answer:** `dict[key] = [(timestamp, value)]` + binary search khi get
**Follow-up:** "Tại sao binary search được? Timestamp có guarantee gì?"
```python
from collections import defaultdict
import bisect
class TimeMap:
    def __init__(self):
        self.store = defaultdict(list)  # key -> [(ts, val)]
```

### DS-M04: Design Underground System *(LeetCode 1396)*
**Câu hỏi:** Track hành trình tàu điện: `checkIn(id, station, t)`, `checkOut(id, station, t)`, `getAverageTime(s1, s2)`. Tính average travel time giữa 2 station.
**Keywords:** 2 dicts: `check_in_data[id]=(station,t)`, `travel_data[(s1,s2)]=(total,count)`
**Follow-up:** "Memory footprint của solution này? Cách optimize nếu có millions of passengers?"

### DS-M05: Two Pointers & Sliding Window
**Câu hỏi:** Kỹ thuật Two Pointers là gì? Cho ví dụ bài toán áp dụng được.
**Keywords:** sorted array, convergent pointers, sliding window variant
**Follow-up:** "Giải bài 'find pair sum to target' trong O(n) time, O(1) space?"

---

## HARD

### DS-H01: LRU Cache *(LeetCode 146)*
**Câu hỏi:** Design và implement một LRU Cache với `get`/`put` O(1).
**Keywords:** doubly linked list + hashmap, `collections.OrderedDict`, `move_to_end()`
**Expected answer:**
```python
from collections import OrderedDict
class LRUCache:
    def __init__(self, capacity: int):
        self.cap = capacity
        self.cache = OrderedDict()

    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.cap:
            self.cache.popitem(last=False)
```
**Follow-up:** "Tại sao cần doubly linked list? Singly linked list không đủ?"
**CV link:** "Bạn đã dùng caching strategy nào ở Sidecardata? Redis eviction policy là gì?"

### DS-H02: Insert Delete GetRandom O(1) *(LeetCode 380)*
**Câu hỏi:** Design một data structure với `insert`, `remove`, `getRandom` tất cả O(1) average.
**Keywords:** dict (val→index) + list (index→val), swap-with-last khi delete
**Expected answer:**
```python
import random
class RandomizedSet:
    def __init__(self):
        self.val_to_idx = {}
        self.vals = []

    def insert(self, val: int) -> bool:
        if val in self.val_to_idx:
            return False
        self.val_to_idx[val] = len(self.vals)
        self.vals.append(val)
        return True

    def remove(self, val: int) -> bool:
        if val not in self.val_to_idx:
            return False
        idx = self.val_to_idx[val]
        last = self.vals[-1]
        self.vals[idx] = last
        self.val_to_idx[last] = idx
        self.vals.pop()
        del self.val_to_idx[val]
        return True

    def getRandom(self) -> int:
        return random.choice(self.vals)
```
**Follow-up:** "Tại sao swap-with-last khi remove? Dùng list thay vì linked list vì sao?"

### DS-H03: Insert Delete GetRandom O(1) - Duplicates Allowed *(LeetCode 381)*
**Câu hỏi:** Tương tự DS-H02 nhưng cho phép duplicate values. `getRandom` phải trả về uniformly random.
**Keywords:** `dict[val] = set(indices)`, swap logic phức tạp hơn
**Follow-up:** "Phần nào thay đổi so với bài không có duplicate? Trade-off về memory?"

### DS-H04: Binary Search Tree & Heap
**Câu hỏi:** Min-heap là gì? Làm thế nào để implement priority queue bằng heap?
**Keywords:** complete binary tree, heapify, O(log n) insert/delete, O(1) peek
**Follow-up:** "Python `heapq` là min-heap hay max-heap? Làm max-heap bằng cách nào?"
```python
import heapq
heap = []
heapq.heappush(heap, 3)
heapq.heappush(heap, 1)
heapq.heappush(heap, 2)
print(heapq.heappop(heap))  # 1
# Max-heap: negate values
heapq.heappush(heap, -5)
```
