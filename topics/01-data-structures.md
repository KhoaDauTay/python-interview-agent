# Data Structures — Question Bank

## EASY

### DS-E01: Array vs Linked List
**Câu hỏi:** Sự khác biệt giữa Array và Linked List là gì? Khi nào nên dùng cái nào?
**Keywords:** random access, O(1) lookup, O(n) insert, memory contiguous
**Follow-up:** "Doubly linked list giải quyết vấn đề gì mà singly linked list không làm được?"

### DS-E02: Stack và Queue
**Câu hỏi:** Mô tả Stack và Queue. Cho ví dụ use-case thực tế của từng loại.
**Keywords:** LIFO, FIFO, call stack, BFS, DFS
**Follow-up:** "Dùng gì để implement một Queue hiệu quả trong Python?"

### DS-E03: Hash Table cơ bản
**Câu hỏi:** Hash table hoạt động như thế nào? Collision xảy ra khi nào và xử lý thế nào?
**Keywords:** hash function, collision, chaining, open addressing, load factor
**Follow-up:** "Python dict có phải là hash table không? Nó handle collision thế nào?"

---

## MEDIUM

### DS-M01: Binary Search Tree
**Câu hỏi:** BST là gì? Viết hàm search trong BST (có thể dùng pseudo-code). Time complexity?
**Keywords:** left < root < right, O(log n) average, O(n) worst case, balanced
**Follow-up:** "Khi nào BST bị degenerate? Cách khắc phục?"

### DS-M02: Heap
**Câu hỏi:** Min-heap là gì? Làm thế nào để implement priority queue bằng heap?
**Keywords:** complete binary tree, heapify, O(log n) insert/delete, O(1) peek
**Follow-up:** "Python `heapq` là min-heap hay max-heap? Làm max-heap bằng cách nào?"
**Code example:**
```python
import heapq
heap = []
heapq.heappush(heap, 3)
heapq.heappush(heap, 1)
heapq.heappush(heap, 2)
print(heapq.heappop(heap))  # 1
```

### DS-M03: Graph representation
**Câu hỏi:** Có những cách nào để biểu diễn Graph? Ưu nhược điểm của mỗi cách?
**Keywords:** adjacency matrix O(V²), adjacency list O(V+E), edge list, sparse vs dense
**Follow-up:** "Với social network 1 tỷ user, bạn chọn cách nào? Tại sao?"

### DS-M04: Two Pointers
**Câu hỏi:** Kỹ thuật Two Pointers là gì? Cho ví dụ bài toán áp dụng được.
**Keywords:** sorted array, convergent pointers, sliding window variant
**Follow-up:** "Giải bài 'find pair sum to target' trong O(n) time, O(1) space?"

---

## HARD

### DS-H01: LRU Cache
**Câu hỏi:** Design và implement một LRU Cache với get/put O(1).
**Keywords:** doubly linked list + hashmap, OrderedDict in Python
**Follow-up:** "Python có built-in gì để implement LRU không?"
**Expected answer:** `collections.OrderedDict` hoặc `functools.lru_cache`

### DS-H02: Trie
**Câu hỏi:** Trie data structure là gì? Khi nào dùng Trie thay vì Hash Table?
**Keywords:** prefix tree, autocomplete, O(m) search, space tradeoff
**Follow-up:** "Implement insert và search cho Trie bằng Python"

### DS-H03: Segment Tree
**Câu hỏi:** Segment Tree giải quyết bài toán gì? Time/space complexity?
**Keywords:** range query, O(log n) update/query, lazy propagation
**Follow-up:** "Khi nào dùng Segment Tree vs Fenwick Tree?"
