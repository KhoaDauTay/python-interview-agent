# Algorithms & Complexity — Question Bank
> CV context: Khoa cần cải thiện DP và binary search. Interviewer nhắc "tận dụng dictionary" → focus on hashmap-based optimizations.

---

## EASY

### AL-E01: Big-O cơ bản
**Câu hỏi:** Giải thích O(1), O(n), O(n²), O(log n). Cho ví dụ code của từng loại.
**Keywords:** time complexity, space complexity, asymptotic notation
**Follow-up:** "O(n log n) xuất hiện ở đâu? Tại sao sort tốt nhất là O(n log n)?"

### AL-E02: Binary Search cơ bản
**Câu hỏi:** Viết Binary Search. Tại sao nó là O(log n)?
**Keywords:** sorted array, `mid = left + (right-left)//2`, off-by-one
**Expected code:**
```python
def binary_search(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = left + (right - left) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```
**Follow-up:** "Tại sao dùng `left + (right-left)//2` thay vì `(left+right)//2`?"

### AL-E03: Most Frequent Element (Dict pattern)
**Câu hỏi:** Cho list số nguyên, trả về phần tử xuất hiện nhiều nhất. O(n) time.
**Keywords:** dict counter, `.get(k, 0) + 1`, `max(d, key=d.get)`, `collections.Counter`
**Expected code:**
```python
from collections import Counter
def most_frequent(nums):
    return Counter(nums).most_common(1)[0][0]

# Manual version:
def most_frequent_manual(nums):
    count = {}
    for n in nums:
        count[n] = count.get(n, 0) + 1
    return max(count, key=count.get)
```
**Follow-up:** "Top-K frequent elements thì làm thế nào? O(n log k) solution?"

---

## MEDIUM

### AL-M01: Find Minimum in Rotated Sorted Array *(LeetCode 153)*
**Câu hỏi:** Cho array đã sort rồi bị rotate (e.g. `[4,5,6,7,0,1,2]`), tìm minimum. O(log n).
**Keywords:** binary search, so sánh `nums[mid]` vs `nums[right]`, không dùng `nums[left]`
**Expected code:**
```python
def findMin(nums):
    left, right = 0, len(nums) - 1
    while left < right:
        mid = (left + right) // 2
        if nums[mid] > nums[right]:
            left = mid + 1   # min nằm bên phải
        else:
            right = mid      # mid có thể là min
    return nums[left]
```
**Follow-up:** "Tại sao so sánh với `nums[right]` chứ không phải `nums[left]`? Nếu array không bị rotate thì sao?"

### AL-M02: Sliding Window — Longest Subarray *(LeetCode 1438)*
**Câu hỏi:** Cho array `nums` và `limit`, tìm longest subarray sao cho `max - min <= limit`.
**Keywords:** sliding window + monotonic deque, `collections.deque`, O(n)
**Expected approach:**
```python
from collections import deque
def longestSubarray(nums, limit):
    max_dq, min_dq = deque(), deque()  # decreasing, increasing
    left = res = 0
    for right, n in enumerate(nums):
        while max_dq and nums[max_dq[-1]] <= n: max_dq.pop()
        while min_dq and nums[min_dq[-1]] >= n: min_dq.pop()
        max_dq.append(right)
        min_dq.append(right)
        while nums[max_dq[0]] - nums[min_dq[0]] > limit:
            left += 1
            if max_dq[0] < left: max_dq.popleft()
            if min_dq[0] < left: min_dq.popleft()
        res = max(res, right - left + 1)
    return res
```
**Follow-up:** "Tại sao cần 2 deque? Monotonic deque là gì?"

### AL-M03: Dynamic Programming — Coin Change *(LeetCode 322)*
**Câu hỏi:** Cho coins và amount, tìm số coin ít nhất để tạo amount. Nếu không thể, return -1.
**Keywords:** bottom-up DP, `dp[i] = min(dp[i], dp[i-coin]+1)`, O(amount × coins)
**Expected code:**
```python
def coinChange(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for i in range(1, amount + 1):
        for coin in coins:
            if coin <= i:
                dp[i] = min(dp[i], dp[i - coin] + 1)
    return dp[amount] if dp[amount] != float('inf') else -1
```
**Follow-up:** "Top-down (memoization) vs bottom-up — khi nào dùng cái nào?"

### AL-M04: BFS vs DFS
**Câu hỏi:** So sánh BFS và DFS. Khi nào dùng BFS, khi nào dùng DFS?
**Keywords:** queue vs stack, shortest path, memory usage, tree vs graph
**Follow-up:** "Dùng BFS hay DFS để tìm đường đi ngắn nhất trong unweighted graph?"

### AL-M05: Two Sum variants (Dict pattern)
**Câu hỏi:** Two Sum cơ bản O(n). Sau đó: nếu array sorted thì dùng two pointers thế nào?
**Keywords:** hashmap `{val: index}`, complement lookup, two pointers on sorted
**Expected code:**
```python
def twoSum(nums, target):
    seen = {}  # val -> index
    for i, n in enumerate(nums):
        complement = target - n
        if complement in seen:
            return [seen[complement], i]
        seen[n] = i
```
**Follow-up:** "Three Sum thì sao? Time complexity là gì?"

---

## HARD

### AL-H01: Interleaving String *(LeetCode 97)*
**Câu hỏi:** Cho `s1`, `s2`, `s3` — check xem `s3` có phải là interleaving của `s1` và `s2` không.
**Keywords:** 2D DP, `dp[i][j]` = có thể tạo `s3[:i+j]` từ `s1[:i]` và `s2[:j]`, memoization
**Expected approach:**
```python
def isInterleave(s1, s2, s3):
    m, n = len(s1), len(s2)
    if m + n != len(s3): return False
    dp = [[False] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = True
    for i in range(1, m + 1):
        dp[i][0] = dp[i-1][0] and s1[i-1] == s3[i-1]
    for j in range(1, n + 1):
        dp[0][j] = dp[0][j-1] and s2[j-1] == s3[j-1]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = (dp[i-1][j] and s1[i-1] == s3[i+j-1]) or \
                       (dp[i][j-1] and s2[j-1] == s3[i+j-1])
    return dp[m][n]
```
**Follow-up:** "Space optimize xuống O(n) được không?"

### AL-H02: Dynamic Programming — Fibonacci & Memoization
**Câu hỏi:** DP là gì? Phân biệt top-down (memoization) và bottom-up (tabulation). Demo với Fibonacci.
**Keywords:** overlapping subproblems, optimal substructure, `@functools.lru_cache`
**Expected code:**
```python
# Top-down
from functools import lru_cache
@lru_cache(maxsize=None)
def fib_memo(n):
    if n <= 1: return n
    return fib_memo(n-1) + fib_memo(n-2)

# Bottom-up
def fib_dp(n):
    if n <= 1: return n
    dp = [0, 1]
    for i in range(2, n+1):
        dp.append(dp[-1] + dp[-2])
    return dp[n]
```

### AL-H03: Complexity Analysis nâng cao
**Câu hỏi:** Amortized complexity là gì? Cho ví dụ với dynamic array (Python list append).
**Keywords:** amortized O(1), worst case O(n), aggregate analysis
**Follow-up:** "Celery task queue retry với exponential backoff — complexity là gì khi có N retries?"
**CV link:** "Bạn đã implement exponential backoff ở Sidecardata — giải thích tại sao đó là cách đúng?"
