# Algorithms & Complexity — Question Bank

## EASY

### AL-E01: Big-O cơ bản
**Câu hỏi:** Giải thích O(1), O(n), O(n²), O(log n). Cho ví dụ code của từng loại.
**Keywords:** time complexity, space complexity, asymptotic notation
**Follow-up:** "O(n log n) xuất hiện ở đâu? Tại sao sort tốt nhất là O(n log n)?"

### AL-E02: Binary Search
**Câu hỏi:** Viết Binary Search. Tại sao nó là O(log n)?
**Keywords:** sorted array, mid = left + (right-left)//2, off-by-one
**Follow-up:** "Binary Search có thể áp dụng cho bài toán nào khác ngoài tìm kiếm?"

### AL-E03: Bubble Sort vs Quick Sort
**Câu hỏi:** Tại sao Quick Sort thường nhanh hơn Bubble Sort dù cùng worst-case O(n²)?
**Keywords:** average case O(n log n), cache locality, in-place, pivot selection

---

## MEDIUM

### AL-M01: BFS vs DFS
**Câu hỏi:** So sánh BFS và DFS. Khi nào dùng BFS, khi nào dùng DFS?
**Keywords:** queue vs stack, shortest path, memory usage, tree vs graph
**Follow-up:** "Dùng BFS hay DFS để tìm đường đi ngắn nhất trong unweighted graph?"

### AL-M02: Dynamic Programming
**Câu hỏi:** DP là gì? Phân biệt top-down (memoization) và bottom-up (tabulation).
**Keywords:** overlapping subproblems, optimal substructure, fibonacci example
**Follow-up:** "Cho bài toán Coin Change — bạn tiếp cận DP thế nào?"

### AL-M03: Sliding Window
**Câu hỏi:** Kỹ thuật Sliding Window là gì? Solve bài 'max sum subarray of size k'.
**Keywords:** fixed window, variable window, two pointers relation, O(n)
**Code challenge:**
```
Input: [2, 1, 5, 1, 3, 2], k=3
Output: 9  # [5, 1, 3]
```

### AL-M04: Merge Sort
**Câu hỏi:** Implement Merge Sort. Tại sao nó stable? Nhược điểm so với Quick Sort?
**Keywords:** divide and conquer, O(n log n) guaranteed, O(n) extra space

---

## HARD

### AL-H01: Dijkstra's Algorithm
**Câu hỏi:** Giải thích Dijkstra. Tại sao không hoạt động với negative weights?
**Keywords:** priority queue, greedy, O((V+E) log V), non-negative weights
**Follow-up:** "Thay thế nào cho negative weights? Bellman-Ford là gì?"

### AL-H02: Backtracking
**Câu hỏi:** Backtracking khác với brute force thế nào? Cho ví dụ N-Queens.
**Keywords:** pruning, state space tree, constraint satisfaction
**Follow-up:** "Làm thế nào để tối ưu backtracking bằng pruning?"

### AL-H03: Complexity Analysis nâng cao
**Câu hỏi:** Amortized complexity là gì? Cho ví dụ với dynamic array (Python list append).
**Keywords:** amortized O(1), worst case O(n), aggregate analysis
