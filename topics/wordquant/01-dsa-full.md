# DSA Full — Đề cương phỏng vấn Data Structures & Algorithms

> Mức độ: Easy → Hard | Mục tiêu: nắm đủ để làm LeetCode Medium/Hard và phỏng vấn WorldQuant

---

## 1. Big-O & Complexity Analysis

### Lý thuyết

Big-O notation mô tả **upper bound** của thời gian/không gian chạy khi input size `n` tiến đến vô cực. Interviewer luôn hỏi complexity — phải trả lời ngay lập tức, không cần suy nghĩ lâu.

**Các lớp complexity phổ biến (từ tốt đến xấu):**

| Notation | Tên | Ví dụ |
|----------|-----|-------|
| O(1) | Constant | Hash map lookup, array index |
| O(log n) | Logarithmic | Binary search, BST operations |
| O(n) | Linear | Single loop, linear scan |
| O(n log n) | Linearithmic | Merge sort, heap sort |
| O(n²) | Quadratic | Nested loop, bubble sort |
| O(2^n) | Exponential | Recursive subset enumeration |
| O(n!) | Factorial | Permutation generation |

```python
# O(1) — không phụ thuộc n
def get_first(arr: list) -> int:
    return arr[0]  # luôn 1 bước dù arr có 10 hay 10^9 phần tử

# O(log n) — mỗi bước loại bỏ nửa search space
def binary_search(arr: list[int], target: int) -> int:
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1  # loại nửa trái
        else:
            hi = mid - 1  # loại nửa phải
    return -1

# O(n) — duyệt từng phần tử đúng 1 lần
def find_max(arr: list[int]) -> int:
    max_val = arr[0]
    for x in arr:          # n bước
        if x > max_val:
            max_val = x
    return max_val

# O(n log n) — sort + scan
def find_closest_pair(arr: list[int]) -> tuple[int, int]:
    arr.sort()              # O(n log n)
    min_diff = float('inf')
    result = (arr[0], arr[1])
    for i in range(len(arr) - 1):  # O(n)
        if arr[i+1] - arr[i] < min_diff:
            min_diff = arr[i+1] - arr[i]
            result = (arr[i], arr[i+1])
    return result

# O(n²) — nested loop
def has_duplicate_naive(arr: list[int]) -> bool:
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):  # n*(n-1)/2 bước
            if arr[i] == arr[j]:
                return True
    return False

# O(2^n) — generate all subsets
def all_subsets(arr: list[int]) -> list[list[int]]:
    result = [[]]
    for x in arr:
        # mỗi element nhân đôi số subsets: 2^n subsets tổng cộng
        result += [subset + [x] for subset in result]
    return result
```

### Space Complexity

```python
# O(1) space — in-place, không allocate thêm
def reverse_array(arr: list[int]) -> None:
    lo, hi = 0, len(arr) - 1
    while lo < hi:
        arr[lo], arr[hi] = arr[hi], arr[lo]
        lo += 1
        hi -= 1

# O(n) space — tạo mảng mới
def reverse_array_new(arr: list[int]) -> list[int]:
    return arr[::-1]  # tạo list mới kích thước n

# O(n) space — recursion stack depth = n
def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)  # n stack frames

# O(log n) space — recursion stack depth = log n
def binary_search_recursive(arr, target, lo=0, hi=None) -> int:
    if hi is None:
        hi = len(arr) - 1
    if lo > hi:
        return -1
    mid = (lo + hi) // 2
    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        return binary_search_recursive(arr, target, mid + 1, hi)
    else:
        return binary_search_recursive(arr, target, lo, mid - 1)
```

### Amortized Analysis — Dynamic Array

```python
# Dynamic array (Python list) append: amortized O(1)
# Thỉnh thoảng resize gấp đôi nhưng tính trung bình vẫn O(1)

class DynamicArray:
    """Minh họa amortized O(1) append."""

    def __init__(self):
        self._data = [None] * 1      # capacity ban đầu = 1
        self._size = 0
        self._capacity = 1
        self._total_copies = 0       # đếm tổng số copy operations

    def append(self, val) -> None:
        if self._size == self._capacity:
            # resize: copy tất cả elements sang array mới gấp đôi
            self._capacity *= 2
            new_data = [None] * self._capacity
            for i in range(self._size):
                new_data[i] = self._data[i]
                self._total_copies += 1
            self._data = new_data
        self._data[self._size] = val
        self._size += 1

# Sau n appends, total copies = 1 + 2 + 4 + ... + n = 2n - 1 = O(n)
# Amortized cost per append = O(n) / n = O(1)
```

### Interview Tips

- Luôn nói complexity **trước khi code**: "Approach này O(n²) time O(1) space, tôi có thể tối ưu xuống O(n) bằng hash map."
- Phân biệt **worst case** vs **average case** (quick sort: O(n²) worst nhưng O(n log n) average).
- Khi thấy `n` nhỏ (<= 20): O(2^n) hay O(n!) có thể chấp nhận được.
- Khi thấy sorted array: nghĩ ngay đến binary search — O(log n).

---

## 2. Arrays & Two Pointers

### Lý thuyết

Two pointer là pattern dùng 2 chỉ số để duyệt array hiệu quả. Thay vì O(n²) nested loop, giảm xuống O(n). Có 2 dạng chính: **opposite ends** (hai đầu gặp nhau) và **same direction** (cùng chiều, sliding window).

### Khi nào dùng

- Tìm cặp/bộ số thỏa điều kiện trong sorted array
- Xóa/di chuyển phần tử
- Palindrome check
- Sliding window trên subarray/substring

### Template: Opposite Ends

```python
# Pattern: hai pointer từ hai đầu, tiến vào giữa
def two_sum_sorted(arr: list[int], target: int) -> tuple[int, int]:
    """Tìm 2 chỉ số có tổng = target trong sorted array. O(n) time O(1) space."""
    lo, hi = 0, len(arr) - 1
    while lo < hi:
        s = arr[lo] + arr[hi]
        if s == target:
            return (lo, hi)
        elif s < target:
            lo += 1   # tổng nhỏ quá, tăng lo để tăng tổng
        else:
            hi -= 1   # tổng lớn quá, giảm hi để giảm tổng
    return (-1, -1)

# Ví dụ: Container With Most Water
def max_water(height: list[int]) -> int:
    """LeetCode 11. O(n) time O(1) space."""
    lo, hi = 0, len(height) - 1
    max_area = 0
    while lo < hi:
        area = min(height[lo], height[hi]) * (hi - lo)
        max_area = max(max_area, area)
        # di chuyển pointer phía có height thấp hơn
        # vì giữ pointer cao hơn luôn là lựa chọn tốt hơn
        if height[lo] < height[hi]:
            lo += 1
        else:
            hi -= 1
    return max_area

# 3Sum — sắp xếp + two pointer lồng nhau
def three_sum(nums: list[int]) -> list[list[int]]:
    """Tìm tất cả bộ ba có tổng = 0. O(n²) time O(1) space."""
    nums.sort()
    result = []
    for i in range(len(nums) - 2):
        if i > 0 and nums[i] == nums[i-1]:
            continue  # bỏ qua duplicate ở vị trí i
        lo, hi = i + 1, len(nums) - 1
        while lo < hi:
            s = nums[i] + nums[lo] + nums[hi]
            if s == 0:
                result.append([nums[i], nums[lo], nums[hi]])
                while lo < hi and nums[lo] == nums[lo+1]: lo += 1  # skip dup
                while lo < hi and nums[hi] == nums[hi-1]: hi -= 1  # skip dup
                lo += 1
                hi -= 1
            elif s < 0:
                lo += 1
            else:
                hi -= 1
    return result
```

### Template: Same Direction (Fast/Slow)

```python
# Pattern: slow pointer ghi kết quả, fast pointer duyệt
def remove_duplicates(nums: list[int]) -> int:
    """LeetCode 26. Remove duplicates in-place. O(n) time O(1) space."""
    if not nums:
        return 0
    slow = 0  # slow: vị trí ghi phần tử unique tiếp theo
    for fast in range(1, len(nums)):  # fast: duyệt từng phần tử
        if nums[fast] != nums[slow]:
            slow += 1
            nums[slow] = nums[fast]
    return slow + 1  # số lượng unique elements

def move_zeroes(nums: list[int]) -> None:
    """LeetCode 283. Đẩy tất cả 0 về cuối, giữ thứ tự. O(n) O(1)."""
    slow = 0  # slow: vị trí tiếp theo để đặt non-zero
    for fast in range(len(nums)):
        if nums[fast] != 0:
            nums[slow] = nums[fast]
            slow += 1
    # điền 0 vào phần còn lại
    while slow < len(nums):
        nums[slow] = 0
        slow += 1
```

### Sliding Window — Fixed Size

```python
def max_sum_subarray_k(arr: list[int], k: int) -> int:
    """Tìm subarray độ dài k có tổng lớn nhất. O(n) time O(1) space."""
    # Bước 1: tính tổng cửa sổ đầu tiên
    window_sum = sum(arr[:k])
    max_sum = window_sum

    # Bước 2: trượt cửa sổ — thêm phần tử mới, xóa phần tử cũ
    for i in range(k, len(arr)):
        window_sum += arr[i]        # thêm phần tử vào cửa sổ phải
        window_sum -= arr[i - k]    # xóa phần tử ra khỏi cửa sổ trái
        max_sum = max(max_sum, window_sum)

    return max_sum

def find_anagrams(s: str, p: str) -> list[int]:
    """LeetCode 438. Tìm tất cả starting index của anagram của p trong s. O(n)."""
    from collections import Counter
    if len(p) > len(s):
        return []

    p_count = Counter(p)
    window = Counter(s[:len(p)])
    result = []

    if window == p_count:
        result.append(0)

    for i in range(len(p), len(s)):
        # thêm ký tự mới vào cửa sổ
        new_char = s[i]
        window[new_char] += 1

        # xóa ký tự cũ khỏi cửa sổ
        old_char = s[i - len(p)]
        window[old_char] -= 1
        if window[old_char] == 0:
            del window[old_char]

        if window == p_count:
            result.append(i - len(p) + 1)

    return result
```

### Sliding Window — Variable Size

```python
def length_of_longest_substring(s: str) -> int:
    """LeetCode 3. Substring không có ký tự lặp dài nhất. O(n) O(k)."""
    char_set = set()
    left = 0
    max_len = 0

    for right in range(len(s)):
        # nếu ký tự mới đã trong cửa sổ, co cửa sổ từ trái
        while s[right] in char_set:
            char_set.remove(s[left])
            left += 1
        char_set.add(s[right])
        max_len = max(max_len, right - left + 1)

    return max_len

def min_window_substring(s: str, t: str) -> str:
    """LeetCode 76. Minimum window chứa tất cả ký tự của t. O(n)."""
    from collections import Counter
    if not t or not s:
        return ""

    need = Counter(t)       # ký tự cần trong window
    have = {}               # ký tự đang có trong window
    formed = 0              # số ký tự đã đủ count
    required = len(need)    # số loại ký tự cần đủ

    left = 0
    min_len = float('inf')
    min_left = 0

    for right in range(len(s)):
        c = s[right]
        have[c] = have.get(c, 0) + 1
        if c in need and have[c] == need[c]:
            formed += 1  # loại ký tự c đã đủ

        # co window từ trái khi đã có đủ tất cả ký tự
        while formed == required:
            if right - left + 1 < min_len:
                min_len = right - left + 1
                min_left = left

            lc = s[left]
            have[lc] -= 1
            if lc in need and have[lc] < need[lc]:
                formed -= 1  # thiếu ký tự lc
            left += 1

    return "" if min_len == float('inf') else s[min_left:min_left + min_len]
```

### Prefix Sum

```python
def prefix_sum_range_query(arr: list[int]) -> None:
    """Prefix sum cho phép query range sum O(1) sau O(n) preprocessing."""
    n = len(arr)
    prefix = [0] * (n + 1)
    for i in range(n):
        prefix[i+1] = prefix[i] + arr[i]

    # Query: sum từ index l đến r (inclusive) — O(1)
    def range_sum(l: int, r: int) -> int:
        return prefix[r+1] - prefix[l]

    # Ví dụ
    arr_ex = [1, 2, 3, 4, 5]
    prefix_ex = [0, 1, 3, 6, 10, 15]
    print(range_sum(1, 3))  # 2+3+4 = 9

def subarray_sum_equals_k(nums: list[int], k: int) -> int:
    """LeetCode 560. Đếm số subarray có tổng = k. O(n) O(n)."""
    from collections import defaultdict
    count = defaultdict(int)
    count[0] = 1       # prefix sum = 0 xuất hiện 1 lần (trước phần tử đầu)
    prefix = 0
    result = 0

    for num in nums:
        prefix += num
        # nếu prefix - k đã từng xuất hiện, có subarray với tổng = k
        result += count[prefix - k]
        count[prefix] += 1

    return result
```

### Kadane's Algorithm — Max Subarray

```python
def max_subarray(nums: list[int]) -> int:
    """LeetCode 53. O(n) time O(1) space."""
    # Ý tưởng: tại mỗi vị trí, quyết định: nối tiếp subarray hiện tại hay bắt đầu mới
    max_sum = nums[0]
    current = nums[0]

    for num in nums[1:]:
        # nếu current < 0: tốt hơn là bắt đầu lại từ num
        current = max(num, current + num)
        max_sum = max(max_sum, current)

    return max_sum

def max_subarray_with_indices(nums: list[int]) -> tuple[int, int, int]:
    """Trả về (max_sum, start, end) của subarray."""
    max_sum = nums[0]
    current = nums[0]
    start = end = 0
    temp_start = 0

    for i in range(1, len(nums)):
        if current + nums[i] < nums[i]:
            current = nums[i]
            temp_start = i  # bắt đầu subarray mới
        else:
            current += nums[i]

        if current > max_sum:
            max_sum = current
            start = temp_start
            end = i

    return max_sum, start, end
```

---

## 3. Hash Map & Hash Set

### Lý thuyết

Hash map lưu key-value với lookup/insert/delete O(1) trung bình (O(n) worst case do collision). Hash set lưu unique keys với O(1) lookup.

### Khi nào dùng HashMap thay vì Array

- Cần tra cứu nhanh theo key tùy ý (không phải index số)
- Đếm tần suất phần tử
- Cache kết quả đã tính (memoization)
- Tìm pair/complement (Two Sum)
- Group các phần tử liên quan

### Counting Frequency

```python
from collections import Counter, defaultdict

def top_k_frequent(nums: list[int], k: int) -> list[int]:
    """LeetCode 347. O(n log k) với heap, hoặc O(n) với bucket sort."""
    count = Counter(nums)

    # Cách 1: dùng heap — O(n log k)
    import heapq
    return [x for x, _ in heapq.nlargest(k, count.items(), key=lambda p: p[1])]

def character_frequency(s: str) -> dict[str, int]:
    """Đếm tần suất ký tự — Counter tự động."""
    freq = Counter(s)
    # Counter({'a': 3, 'b': 2, 'c': 1}) cho "aaabbc"
    return dict(freq.most_common())  # sắp xếp theo tần suất giảm dần
```

### Two Sum và Variants

```python
def two_sum(nums: list[int], target: int) -> list[int]:
    """LeetCode 1. O(n) time O(n) space."""
    seen = {}  # value -> index
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []

def two_sum_all_pairs(nums: list[int], target: int) -> list[tuple[int, int]]:
    """Tìm TẤT CẢ các cặp có tổng = target."""
    seen = defaultdict(list)
    result = []
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            for j in seen[complement]:
                result.append((j, i))
        seen[num].append(i)
    return result

def four_sum_count(A, B, C, D):
    """LeetCode 454. Đếm bộ bốn (i,j,k,l) có A[i]+B[j]+C[k]+D[l]=0. O(n²)."""
    ab_sum = defaultdict(int)
    for a in A:
        for b in B:
            ab_sum[a + b] += 1  # đếm mọi tổng a+b

    count = 0
    for c in C:
        for d in D:
            count += ab_sum[-(c + d)]  # tìm complement
    return count
```

### Grouping Anagrams

```python
def group_anagrams(strs: list[str]) -> list[list[str]]:
    """LeetCode 49. O(n * k log k) với k = max string length."""
    groups = defaultdict(list)
    for s in strs:
        key = tuple(sorted(s))   # anagram có cùng sorted key
        groups[key].append(s)
    return list(groups.values())

def group_anagrams_faster(strs: list[str]) -> list[list[str]]:
    """O(n * k) — dùng count array thay vì sort."""
    groups = defaultdict(list)
    for s in strs:
        count = [0] * 26
        for c in s:
            count[ord(c) - ord('a')] += 1
        key = tuple(count)  # unique key cho mỗi nhóm anagram
        groups[key].append(s)
    return list(groups.values())
```

### defaultdict và Counter Tricks

```python
from collections import defaultdict, Counter, OrderedDict

# defaultdict — tự tạo default value khi key chưa tồn tại
graph = defaultdict(list)    # adjacency list cho graph
graph['A'].append('B')       # không cần check nếu 'A' đã tồn tại

count = defaultdict(int)     # đếm — không cần khởi tạo
count['apple'] += 1          # tự động bắt đầu từ 0

nested = defaultdict(lambda: defaultdict(int))  # nested dict
nested['row']['col'] += 1

# Counter tricks
c1 = Counter("aabbc")
c2 = Counter("abccd")

# Gộp counters
combined = c1 + c2          # {'a': 3, 'b': 3, 'c': 3, 'd': 1}

# Trừ counters (chỉ giữ positive)
diff = c1 - c2              # {'a': 1, 'b': 1}

# Intersection (min của mỗi key)
common = c1 & c2            # {'a': 1, 'b': 1, 'c': 1}

# most_common
print(c1.most_common(2))    # [('a', 2), ('b', 2)]

# elements() — expand về list
print(list(c1.elements()))  # ['a', 'a', 'b', 'b', 'c']

# Kiểm tra anagram
def is_anagram(s: str, t: str) -> bool:
    return Counter(s) == Counter(t)

# LRU Cache đơn giản với OrderedDict
class LRUCache:
    def __init__(self, capacity: int):
        self.cap = capacity
        self.cache = OrderedDict()

    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)  # đánh dấu là recently used
        return self.cache[key]

    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.cap:
            self.cache.popitem(last=False)  # xóa oldest (phần đầu)
```

---

## 4. Stack & Queue

### Lý thuyết

- **Stack** (LIFO): push/pop từ cùng một đầu. Python dùng `list` hoặc `deque`.
- **Queue** (FIFO): enqueue một đầu, dequeue đầu kia. Python dùng `collections.deque`.
- **Monotonic stack**: stack duy trì tính đơn điệu (tăng hoặc giảm) — mạnh cho bài "next greater/smaller element".

### Monotonic Stack — Next Greater Element

```python
def next_greater_element(nums: list[int]) -> list[int]:
    """LeetCode 496. Với mỗi phần tử, tìm phần tử lớn hơn đầu tiên ở bên phải. O(n)."""
    n = len(nums)
    result = [-1] * n
    stack = []  # stack chứa indices, duy trì thứ tự GIẢM dần về giá trị

    for i in range(n):
        # pop khi nums[i] lớn hơn phần tử ở đỉnh stack
        while stack and nums[i] > nums[stack[-1]]:
            idx = stack.pop()
            result[idx] = nums[i]  # nums[i] là "next greater" của nums[idx]
        stack.append(i)

    return result

def largest_rectangle_histogram(heights: list[int]) -> int:
    """LeetCode 84. Hình chữ nhật lớn nhất trong histogram. O(n)."""
    stack = []   # monotonic increasing stack — chứa indices
    max_area = 0
    heights = heights + [0]  # sentinel: buộc xử lý tất cả phần tử cuối

    for i, h in enumerate(heights):
        while stack and heights[stack[-1]] > h:
            height = heights[stack.pop()]
            # width = từ phần tử tiếp theo trong stack đến i
            width = i if not stack else i - stack[-1] - 1
            max_area = max(max_area, height * width)
        stack.append(i)

    return max_area

def daily_temperatures(temperatures: list[int]) -> list[int]:
    """LeetCode 739. Số ngày chờ nhiệt độ tăng. O(n)."""
    result = [0] * len(temperatures)
    stack = []  # indices, monotonic decreasing

    for i, t in enumerate(temperatures):
        while stack and temperatures[stack[-1]] < t:
            idx = stack.pop()
            result[idx] = i - idx  # số ngày chờ
        stack.append(i)

    return result
```

### Valid Parentheses

```python
def is_valid_parentheses(s: str) -> bool:
    """LeetCode 20. O(n) time O(n) space."""
    stack = []
    pairs = {')': '(', ']': '[', '}': '{'}

    for c in s:
        if c in '([{':
            stack.append(c)
        elif c in ')]}':
            if not stack or stack[-1] != pairs[c]:
                return False
            stack.pop()

    return len(stack) == 0

def min_add_to_make_valid(s: str) -> int:
    """LeetCode 921. Số lượng '(' hoặc ')' cần thêm để valid. O(n) O(1)."""
    open_count = 0   # '(' chưa match
    close_count = 0  # ')' chưa match

    for c in s:
        if c == '(':
            open_count += 1
        else:  # c == ')'
            if open_count > 0:
                open_count -= 1  # match với '(' gần nhất
            else:
                close_count += 1  # ')' thừa cần thêm '('

    return open_count + close_count
```

### Queue với deque

```python
from collections import deque

# deque: O(1) append và popleft — tốt hơn list.pop(0) là O(n)
q = deque()
q.append(1)        # enqueue từ phải
q.appendleft(0)    # enqueue từ trái (nếu cần)
front = q.popleft()  # dequeue từ trái — O(1)!

# Sliding window maximum dùng monotonic deque
def sliding_window_max(nums: list[int], k: int) -> list[int]:
    """LeetCode 239. Maximum của mọi subarray độ dài k. O(n)."""
    dq = deque()  # lưu indices, duy trì monotonic DECREASING về value
    result = []

    for i, num in enumerate(nums):
        # xóa các index đã ra khỏi cửa sổ
        while dq and dq[0] < i - k + 1:
            dq.popleft()

        # xóa các index có value nhỏ hơn num (chúng không bao giờ là max)
        while dq and nums[dq[-1]] < num:
            dq.pop()

        dq.append(i)

        if i >= k - 1:
            result.append(nums[dq[0]])  # phần tử đầu deque là max của cửa sổ

    return result
```

### Min Stack

```python
class MinStack:
    """LeetCode 155. Stack hỗ trợ getMin() O(1)."""

    def __init__(self):
        self.stack = []      # (value, current_min) tại mỗi vị trí
        self.min_stack = []  # track minimum hiện tại

    def push(self, val: int) -> None:
        self.stack.append(val)
        # min mới = min của (val, min hiện tại)
        current_min = val if not self.min_stack else min(val, self.min_stack[-1])
        self.min_stack.append(current_min)

    def pop(self) -> None:
        self.stack.pop()
        self.min_stack.pop()

    def top(self) -> int:
        return self.stack[-1]

    def getMin(self) -> int:
        return self.min_stack[-1]  # O(1)!
```

### BFS dùng Queue

```python
from collections import deque

def bfs_graph(graph: dict, start: str) -> list[str]:
    """BFS duyệt graph. O(V + E)."""
    visited = set([start])
    queue = deque([start])
    order = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return order

def shortest_path(grid: list[list[int]], start: tuple, end: tuple) -> int:
    """BFS tìm đường ngắn nhất trong grid. O(m*n)."""
    rows, cols = len(grid), len(grid[0])
    directions = [(0,1),(0,-1),(1,0),(-1,0)]  # 4 hướng

    queue = deque([(start, 0)])  # (vị trí, số bước)
    visited = {start}

    while queue:
        (r, c), steps = queue.popleft()
        if (r, c) == end:
            return steps
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if (0 <= nr < rows and 0 <= nc < cols
                    and grid[nr][nc] == 0          # 0 = đường đi, 1 = tường
                    and (nr, nc) not in visited):
                visited.add((nr, nc))
                queue.append(((nr, nc), steps + 1))

    return -1  # không tìm thấy đường
```

---

## 5. Linked List

### Lý thuyết

Linked list là cấu trúc node liên kết — O(1) insert/delete khi đã có pointer, O(n) access. Phần lớn bài phỏng vấn dùng slow/fast pointer hoặc reverse.

### Slow/Fast Pointer

```python
from typing import Optional

class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def has_cycle(head: Optional[ListNode]) -> bool:
    """LeetCode 141. Detect cycle. O(n) time O(1) space."""
    slow = fast = head
    while fast and fast.next:
        slow = slow.next        # di chuyển 1 bước
        fast = fast.next.next   # di chuyển 2 bước
        if slow == fast:
            return True         # gặp nhau — có cycle
    return False

def detect_cycle_entry(head: Optional[ListNode]) -> Optional[ListNode]:
    """LeetCode 142. Tìm node bắt đầu cycle. O(n) O(1)."""
    slow = fast = head
    # Phase 1: tìm điểm gặp nhau
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast:
            break
    else:
        return None  # không có cycle

    # Phase 2: reset slow về head, di chuyển cả hai tốc độ 1
    # Toán học: khoảng cách từ head đến entry = khoảng cách từ meeting point đến entry
    slow = head
    while slow != fast:
        slow = slow.next
        fast = fast.next
    return slow  # entry point

def find_middle(head: Optional[ListNode]) -> Optional[ListNode]:
    """Tìm node giữa. O(n) O(1). Nếu chẵn: trả về node thứ hai trong đôi giữa."""
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
    return slow
```

### Reverse Linked List

```python
def reverse_list_iterative(head: Optional[ListNode]) -> Optional[ListNode]:
    """LeetCode 206. O(n) time O(1) space."""
    prev = None
    curr = head
    while curr:
        next_node = curr.next  # lưu next trước khi thay đổi
        curr.next = prev       # đảo chiều pointer
        prev = curr            # di chuyển prev lên
        curr = next_node       # di chuyển curr lên
    return prev  # prev là head mới

def reverse_list_recursive(head: Optional[ListNode]) -> Optional[ListNode]:
    """O(n) time O(n) space (call stack)."""
    if not head or not head.next:
        return head
    new_head = reverse_list_recursive(head.next)  # reverse phần còn lại
    head.next.next = head  # node tiếp theo trỏ ngược lại head
    head.next = None        # ngắt liên kết cũ
    return new_head

def reverse_between(head: Optional[ListNode], left: int, right: int) -> Optional[ListNode]:
    """LeetCode 92. Reverse từ position left đến right. O(n) O(1)."""
    dummy = ListNode(0)
    dummy.next = head
    prev = dummy

    # Di chuyển đến node trước left
    for _ in range(left - 1):
        prev = prev.next

    curr = prev.next  # node đầu tiên cần reverse

    # Reverse (right - left) lần
    for _ in range(right - left):
        next_node = curr.next
        curr.next = next_node.next
        next_node.next = prev.next
        prev.next = next_node

    return dummy.next
```

### Merge Sorted Lists

```python
def merge_two_sorted_lists(l1: Optional[ListNode], l2: Optional[ListNode]) -> Optional[ListNode]:
    """LeetCode 21. O(n+m) time O(1) space."""
    dummy = ListNode(0)
    curr = dummy

    while l1 and l2:
        if l1.val <= l2.val:
            curr.next = l1
            l1 = l1.next
        else:
            curr.next = l2
            l2 = l2.next
        curr = curr.next

    curr.next = l1 if l1 else l2  # nối phần còn lại
    return dummy.next

def merge_k_sorted_lists(lists: list[Optional[ListNode]]) -> Optional[ListNode]:
    """LeetCode 23. Dùng heap. O(n log k) với n = tổng nodes, k = số list."""
    import heapq
    heap = []  # (value, list_index, node)

    for i, node in enumerate(lists):
        if node:
            heapq.heappush(heap, (node.val, i, node))

    dummy = ListNode(0)
    curr = dummy

    while heap:
        val, i, node = heapq.heappop(heap)
        curr.next = node
        curr = curr.next
        if node.next:
            heapq.heappush(heap, (node.next.val, i, node.next))

    return dummy.next
```

### Common Pitfalls với None Checks

```python
# SILL hay quên: check None trước khi truy cập .next
def bad_practice(head: Optional[ListNode]) -> int:
    while head.next:  # ERROR nếu head là None!
        head = head.next
    return head.val   # ERROR nếu head là None!

def good_practice(head: Optional[ListNode]) -> Optional[int]:
    if not head:
        return None
    while head.next:
        head = head.next
    return head.val

# Dummy node tránh edge case khi insert/delete đầu list
def delete_node_val(head: Optional[ListNode], val: int) -> Optional[ListNode]:
    dummy = ListNode(0)
    dummy.next = head  # dummy.next = head tránh phải xử lý riêng trường hợp xóa head
    curr = dummy
    while curr.next:
        if curr.next.val == val:
            curr.next = curr.next.next  # bỏ qua node cần xóa
        else:
            curr = curr.next
    return dummy.next
```

---

## 6. Binary Trees

### Lý thuyết

Tree là cấu trúc đệ quy — hầu hết bài đều giải bằng đệ quy. Ba phép duyệt DFS: preorder (root→left→right), inorder (left→root→right — cho BST sorted order), postorder (left→right→root — tốt khi cần thông tin từ con trước).

```python
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
```

### DFS Templates

```python
# Preorder — root trước, dùng khi serialize/copy tree
def preorder_recursive(root: Optional[TreeNode]) -> list[int]:
    if not root:
        return []
    return [root.val] + preorder_recursive(root.left) + preorder_recursive(root.right)

def preorder_iterative(root: Optional[TreeNode]) -> list[int]:
    """Dùng stack — dễ nhớ: push right trước left."""
    if not root:
        return []
    result = []
    stack = [root]
    while stack:
        node = stack.pop()
        result.append(node.val)
        if node.right: stack.append(node.right)  # right trước vì LIFO
        if node.left:  stack.append(node.left)
    return result

# Inorder — left→root→right, cho BST: kết quả sorted
def inorder_recursive(root: Optional[TreeNode]) -> list[int]:
    if not root:
        return []
    return inorder_recursive(root.left) + [root.val] + inorder_recursive(root.right)

def inorder_iterative(root: Optional[TreeNode]) -> list[int]:
    result = []
    stack = []
    curr = root
    while curr or stack:
        # đi hết sang trái
        while curr:
            stack.append(curr)
            curr = curr.left
        # xử lý node
        curr = stack.pop()
        result.append(curr.val)
        # chuyển sang right subtree
        curr = curr.right
    return result

# Postorder — left→right→root, dùng khi xóa tree, tính kích thước subtree
def postorder_recursive(root: Optional[TreeNode]) -> list[int]:
    if not root:
        return []
    return postorder_recursive(root.left) + postorder_recursive(root.right) + [root.val]

def postorder_iterative(root: Optional[TreeNode]) -> list[int]:
    """Trick: reverse của preorder (right trước left)."""
    if not root:
        return []
    result = []
    stack = [root]
    while stack:
        node = stack.pop()
        result.append(node.val)
        if node.left:  stack.append(node.left)   # left trước (sẽ bị reverse)
        if node.right: stack.append(node.right)
    return result[::-1]  # reverse để được postorder
```

### BFS Level Order Traversal

```python
from collections import deque

def level_order(root: Optional[TreeNode]) -> list[list[int]]:
    """LeetCode 102. O(n) time O(n) space."""
    if not root:
        return []
    result = []
    queue = deque([root])

    while queue:
        level_size = len(queue)  # số node tại level hiện tại
        level = []
        for _ in range(level_size):
            node = queue.popleft()
            level.append(node.val)
            if node.left:  queue.append(node.left)
            if node.right: queue.append(node.right)
        result.append(level)

    return result

def zigzag_level_order(root: Optional[TreeNode]) -> list[list[int]]:
    """LeetCode 103. Level chẵn: trái→phải, level lẻ: phải→trái."""
    if not root:
        return []
    result = []
    queue = deque([root])
    left_to_right = True

    while queue:
        level_size = len(queue)
        level = deque()
        for _ in range(level_size):
            node = queue.popleft()
            if left_to_right:
                level.append(node.val)
            else:
                level.appendleft(node.val)  # insert từ trái = reverse order
            if node.left:  queue.append(node.left)
            if node.right: queue.append(node.right)
        result.append(list(level))
        left_to_right = not left_to_right

    return result
```

### Height, Diameter, Path Sum

```python
def max_depth(root: Optional[TreeNode]) -> int:
    """LeetCode 104. O(n)."""
    if not root:
        return 0
    return 1 + max(max_depth(root.left), max_depth(root.right))

def diameter_of_binary_tree(root: Optional[TreeNode]) -> int:
    """LeetCode 543. Đường dài nhất giữa 2 node (không cần qua root). O(n)."""
    max_diameter = [0]  # dùng list để mutate bên trong nested function

    def height(node: Optional[TreeNode]) -> int:
        if not node:
            return 0
        left_h = height(node.left)
        right_h = height(node.right)
        # diameter qua node này = left_h + right_h
        max_diameter[0] = max(max_diameter[0], left_h + right_h)
        return 1 + max(left_h, right_h)

    height(root)
    return max_diameter[0]

def has_path_sum(root: Optional[TreeNode], target: int) -> bool:
    """LeetCode 112. O(n)."""
    if not root:
        return False
    if not root.left and not root.right:   # leaf node
        return root.val == target
    return (has_path_sum(root.left, target - root.val) or
            has_path_sum(root.right, target - root.val))

def max_path_sum(root: Optional[TreeNode]) -> int:
    """LeetCode 124. Path sum lớn nhất — path có thể không qua root. O(n)."""
    max_sum = [float('-inf')]

    def gain(node: Optional[TreeNode]) -> int:
        """Trả về gain tối đa nếu extend path qua node này về phía parent."""
        if not node:
            return 0
        left_gain = max(gain(node.left), 0)   # bỏ qua nhánh âm
        right_gain = max(gain(node.right), 0)
        # path qua node này = left + node + right
        max_sum[0] = max(max_sum[0], node.val + left_gain + right_gain)
        # trả về gain một chiều (chỉ chọn 1 nhánh)
        return node.val + max(left_gain, right_gain)

    gain(root)
    return max_sum[0]
```

### Lowest Common Ancestor (LCA)

```python
def lowest_common_ancestor(
    root: Optional[TreeNode],
    p: TreeNode,
    q: TreeNode
) -> Optional[TreeNode]:
    """LeetCode 236. O(n) O(h) với h = height."""
    if not root:
        return None
    if root == p or root == q:
        return root  # tìm thấy p hoặc q — trả về ngay

    left = lowest_common_ancestor(root.left, p, q)
    right = lowest_common_ancestor(root.right, p, q)

    if left and right:
        return root  # p và q ở hai nhánh khác nhau — root là LCA
    return left if left else right  # một trong hai nhánh chứa cả p và q
```

---

## 7. Binary Search Trees

### Lý thuyết & Properties

BST property: với mỗi node, **tất cả** node trong left subtree < node.val, **tất cả** node trong right subtree > node.val. Inorder traversal của BST cho dãy sorted.

```
      5
     / \
    3   7
   / \ / \
  2  4 6  8
```

Inorder: [2, 3, 4, 5, 6, 7, 8] — sorted!

### Search, Insert, Delete

```python
def search_bst(root: Optional[TreeNode], val: int) -> Optional[TreeNode]:
    """O(h) — h = height. Balanced: O(log n), skewed: O(n)."""
    if not root or root.val == val:
        return root
    if val < root.val:
        return search_bst(root.left, val)
    else:
        return search_bst(root.right, val)

def insert_bst(root: Optional[TreeNode], val: int) -> TreeNode:
    """O(h). Luôn insert tại leaf."""
    if not root:
        return TreeNode(val)
    if val < root.val:
        root.left = insert_bst(root.left, val)
    elif val > root.val:
        root.right = insert_bst(root.right, val)
    return root

def delete_bst(root: Optional[TreeNode], val: int) -> Optional[TreeNode]:
    """O(h). Ba case: leaf, 1 con, 2 con."""
    if not root:
        return None
    if val < root.val:
        root.left = delete_bst(root.left, val)
    elif val > root.val:
        root.right = delete_bst(root.right, val)
    else:
        # Tìm thấy node cần xóa
        if not root.left:
            return root.right    # thay bằng right child
        if not root.right:
            return root.left     # thay bằng left child
        # Có 2 con: thay bằng inorder successor (min của right subtree)
        successor = root.right
        while successor.left:
            successor = successor.left
        root.val = successor.val           # copy giá trị
        root.right = delete_bst(root.right, successor.val)  # xóa successor
    return root
```

### Validation

```python
def is_valid_bst(root: Optional[TreeNode]) -> bool:
    """LeetCode 98. O(n) O(h)."""
    def validate(node: Optional[TreeNode], min_val: float, max_val: float) -> bool:
        if not node:
            return True
        if not (min_val < node.val < max_val):
            return False
        return (validate(node.left, min_val, node.val) and
                validate(node.right, node.val, max_val))

    return validate(root, float('-inf'), float('inf'))
```

### Kth Smallest/Largest

```python
def kth_smallest(root: Optional[TreeNode], k: int) -> int:
    """LeetCode 230. Inorder traversal, lấy phần tử thứ k. O(k) O(h)."""
    stack = []
    curr = root
    count = 0

    while curr or stack:
        while curr:
            stack.append(curr)
            curr = curr.left
        curr = stack.pop()
        count += 1
        if count == k:
            return curr.val
        curr = curr.right

    return -1  # không bao giờ đến đây nếu k hợp lệ

def kth_largest(root: Optional[TreeNode], k: int) -> int:
    """Reverse inorder: right→root→left."""
    stack = []
    curr = root
    count = 0
    while curr or stack:
        while curr:
            stack.append(curr)
            curr = curr.right  # đi sang phải trước
        curr = stack.pop()
        count += 1
        if count == k:
            return curr.val
        curr = curr.left
    return -1
```

### BST vs Sorted Array Tradeoffs

| Operation | Sorted Array | Balanced BST |
|-----------|-------------|-------------|
| Search | O(log n) | O(log n) |
| Insert | O(n) | O(log n) |
| Delete | O(n) | O(log n) |
| Min/Max | O(1) | O(log n) |
| Range query | O(log n + k) | O(log n + k) |
| Space | O(n) | O(n) |

Dùng sorted array khi data static (không insert/delete). Dùng BST khi cần dynamic updates.

---

## 8. Heaps / Priority Queue

### Lý thuyết

Heap là complete binary tree thỏa heap property. Python `heapq` là **min heap**. Max heap bằng cách negate giá trị.

- `heapq.heappush(heap, val)` — O(log n)
- `heapq.heappop(heap)` — O(log n), trả về min
- `heapq.heappushpop(heap, val)` — O(log n), push rồi pop min
- `heapq.heapify(arr)` — O(n), convert list thành heap in-place

### Min Heap vs Max Heap trong Python

```python
import heapq

# Min heap — mặc định
min_heap = []
heapq.heappush(min_heap, 3)
heapq.heappush(min_heap, 1)
heapq.heappush(min_heap, 2)
print(heapq.heappop(min_heap))  # 1 — smallest

# Max heap — negate giá trị
max_heap = []
heapq.heappush(max_heap, -3)
heapq.heappush(max_heap, -1)
heapq.heappush(max_heap, -2)
print(-heapq.heappop(max_heap))  # 3 — largest

# Heap với tuple (priority, data)
task_queue = []
heapq.heappush(task_queue, (3, "low priority task"))
heapq.heappush(task_queue, (1, "urgent task"))
heapq.heappush(task_queue, (2, "normal task"))
priority, task = heapq.heappop(task_queue)
print(task)  # "urgent task"
```

### K Largest/Smallest Elements

```python
def k_largest(nums: list[int], k: int) -> list[int]:
    """O(n log k) — dùng min heap size k."""
    # Giữ min heap size k — phần tử nhỏ nhất trong heap là threshold
    heap = nums[:k]
    heapq.heapify(heap)       # O(k)

    for num in nums[k:]:
        if num > heap[0]:     # lớn hơn min hiện tại?
            heapq.heapreplace(heap, num)  # thay thế min bằng num — O(log k)

    return sorted(heap, reverse=True)

def k_smallest(nums: list[int], k: int) -> list[int]:
    """O(n log k) — dùng max heap size k."""
    heap = [-num for num in nums[:k]]
    heapq.heapify(heap)

    for num in nums[k:]:
        if -num > heap[0]:    # -num > max hiện tại nghĩa là num < min hiện tại
            heapq.heapreplace(heap, -num)

    return sorted(-num for num in heap)

# Cách ngắn hơn với nlargest/nsmallest
def k_largest_simple(nums: list[int], k: int) -> list[int]:
    return heapq.nlargest(k, nums)   # O(n log k)

def k_smallest_simple(nums: list[int], k: int) -> list[int]:
    return heapq.nsmallest(k, nums)  # O(n log k)
```

### Merge K Sorted Lists

```python
def merge_k_sorted_arrays(arrays: list[list[int]]) -> list[int]:
    """O(n log k) với n = tổng phần tử, k = số array."""
    heap = []
    result = []

    # Khởi tạo heap với phần tử đầu của mỗi array
    for i, arr in enumerate(arrays):
        if arr:
            heapq.heappush(heap, (arr[0], i, 0))  # (value, array_idx, element_idx)

    while heap:
        val, arr_idx, elem_idx = heapq.heappop(heap)
        result.append(val)
        # Thêm phần tử tiếp theo của cùng array vào heap
        if elem_idx + 1 < len(arrays[arr_idx]):
            next_val = arrays[arr_idx][elem_idx + 1]
            heapq.heappush(heap, (next_val, arr_idx, elem_idx + 1))

    return result
```

### Top K Frequent Elements

```python
def top_k_frequent_heap(nums: list[int], k: int) -> list[int]:
    """LeetCode 347. O(n log k)."""
    from collections import Counter
    count = Counter(nums)

    # Min heap size k theo frequency
    heap = []
    for num, freq in count.items():
        heapq.heappush(heap, (freq, num))
        if len(heap) > k:
            heapq.heappop(heap)  # loại phần tử có frequency thấp nhất

    return [num for freq, num in heap]

def top_k_frequent_bucket(nums: list[int], k: int) -> list[int]:
    """O(n) — bucket sort theo frequency."""
    from collections import Counter
    count = Counter(nums)
    buckets = [[] for _ in range(len(nums) + 1)]

    for num, freq in count.items():
        buckets[freq].append(num)

    result = []
    for freq in range(len(buckets) - 1, 0, -1):
        result.extend(buckets[freq])
        if len(result) >= k:
            break
    return result[:k]

def find_median_from_stream():
    """LeetCode 295. MedianFinder dùng 2 heaps. O(log n) add, O(1) findMedian."""
    class MedianFinder:
        def __init__(self):
            self.small = []   # max heap (negate) — half nhỏ hơn
            self.large = []   # min heap — half lớn hơn

        def addNum(self, num: int) -> None:
            # Push vào small (max heap)
            heapq.heappush(self.small, -num)
            # Balance: small's max phải <= large's min
            if self.small and self.large and (-self.small[0] > self.large[0]):
                heapq.heappush(self.large, -heapq.heappop(self.small))
            # Balance size: small nhiều hơn large tối đa 1
            if len(self.small) > len(self.large) + 1:
                heapq.heappush(self.large, -heapq.heappop(self.small))
            elif len(self.large) > len(self.small):
                heapq.heappush(self.small, -heapq.heappop(self.large))

        def findMedian(self) -> float:
            if len(self.small) > len(self.large):
                return -self.small[0]
            return (-self.small[0] + self.large[0]) / 2.0

    return MedianFinder()
```

---

## 9. Graphs

### Representation

```python
# Adjacency List — thường dùng nhất: O(V+E) space
graph_adj_list = {
    'A': ['B', 'C'],
    'B': ['A', 'D'],
    'C': ['A', 'D'],
    'D': ['B', 'C'],
}

# Với defaultdict — tự động tạo list rỗng
from collections import defaultdict
graph = defaultdict(list)
edges = [('A', 'B'), ('A', 'C'), ('B', 'D'), ('C', 'D')]
for u, v in edges:
    graph[u].append(v)
    graph[v].append(u)  # undirected: thêm cả chiều ngược

# Adjacency Matrix — O(V²) space, O(1) edge lookup
n = 4  # 4 nodes: 0,1,2,3
matrix = [[0] * n for _ in range(n)]
matrix[0][1] = 1  # edge 0→1
matrix[1][0] = 1  # undirected
```

### DFS Template

```python
def dfs_recursive(graph: dict, start: str, visited: set = None) -> list[str]:
    """O(V+E)."""
    if visited is None:
        visited = set()
    visited.add(start)
    result = [start]
    for neighbor in graph.get(start, []):
        if neighbor not in visited:
            result.extend(dfs_recursive(graph, neighbor, visited))
    return result

def dfs_iterative(graph: dict, start: str) -> list[str]:
    """Dùng stack thay vì call stack — tránh RecursionError với graph lớn."""
    visited = set([start])
    stack = [start]
    result = []

    while stack:
        node = stack.pop()
        result.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                stack.append(neighbor)

    return result

def number_of_islands(grid: list[list[str]]) -> int:
    """LeetCode 200. DFS trên grid. O(m*n)."""
    if not grid:
        return 0
    rows, cols = len(grid), len(grid[0])
    count = 0

    def dfs(r: int, c: int) -> None:
        if r < 0 or r >= rows or c < 0 or c >= cols or grid[r][c] != '1':
            return
        grid[r][c] = '0'  # đánh dấu đã thăm bằng cách đổi thành '0'
        dfs(r+1, c); dfs(r-1, c); dfs(r, c+1); dfs(r, c-1)

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '1':
                dfs(r, c)
                count += 1

    return count
```

### Topological Sort

```python
def topo_sort_kahn(num_nodes: int, edges: list[tuple[int, int]]) -> list[int]:
    """Kahn's algorithm — BFS based. O(V+E)."""
    from collections import deque

    # Xây dựng graph và in-degree
    graph = defaultdict(list)
    in_degree = [0] * num_nodes

    for u, v in edges:
        graph[u].append(v)
        in_degree[v] += 1

    # Bắt đầu với các node có in-degree = 0
    queue = deque([i for i in range(num_nodes) if in_degree[i] == 0])
    topo = []

    while queue:
        node = queue.popleft()
        topo.append(node)
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Nếu topo không chứa tất cả node → có cycle
    return topo if len(topo) == num_nodes else []

def course_schedule(num_courses: int, prerequisites: list[list[int]]) -> bool:
    """LeetCode 207. Có thể hoàn thành tất cả courses không? = Detect cycle."""
    order = topo_sort_kahn(num_courses, [(b, a) for a, b in prerequisites])
    return len(order) == num_courses

def topo_sort_dfs(num_nodes: int, edges: list[tuple[int, int]]) -> list[int]:
    """DFS based topological sort. O(V+E)."""
    graph = defaultdict(list)
    for u, v in edges:
        graph[u].append(v)

    # 0=unvisited, 1=in_progress, 2=done
    state = [0] * num_nodes
    result = []
    has_cycle = [False]

    def dfs(node: int) -> None:
        if state[node] == 2: return    # đã xử lý xong
        if state[node] == 1:           # đang xử lý → cycle!
            has_cycle[0] = True
            return
        state[node] = 1
        for neighbor in graph[node]:
            dfs(neighbor)
        state[node] = 2
        result.append(node)  # post-order = reverse topo order

    for i in range(num_nodes):
        if state[i] == 0:
            dfs(i)

    if has_cycle[0]:
        return []
    return result[::-1]  # reverse vì ta thêm vào result theo post-order
```

### Union-Find / Disjoint Set

```python
class UnionFind:
    """Disjoint Set Union với path compression + union by rank. O(α(n)) per op."""

    def __init__(self, n: int):
        self.parent = list(range(n))  # parent[i] = i ban đầu (mỗi node là root)
        self.rank = [0] * n            # dùng để union by rank
        self.num_components = n

    def find(self, x: int) -> int:
        """Tìm root của x với path compression."""
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # path compression
        return self.parent[x]

    def union(self, x: int, y: int) -> bool:
        """Merge 2 sets. Trả về False nếu đã cùng set (→ cycle)."""
        px, py = self.find(x), self.find(y)
        if px == py:
            return False  # đã cùng component — sẽ tạo cycle nếu thêm edge này

        # Union by rank: nối cây thấp hơn vào cây cao hơn
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1
        self.num_components -= 1
        return True

    def connected(self, x: int, y: int) -> bool:
        return self.find(x) == self.find(y)

def redundant_connection(edges: list[list[int]]) -> list[int]:
    """LeetCode 684. Tìm edge tạo cycle đầu tiên. O(n α(n))."""
    uf = UnionFind(len(edges) + 1)
    for u, v in edges:
        if not uf.union(u, v):
            return [u, v]
    return []
```

### Dijkstra's Shortest Path

```python
def dijkstra(graph: dict[int, list[tuple[int, int]]], src: int) -> dict[int, int]:
    """
    graph[u] = [(v, weight), ...] — weighted adjacency list
    Trả về dict: node → shortest distance từ src. O((V+E) log V).
    """
    import heapq
    dist = {src: 0}
    heap = [(0, src)]  # (distance, node)

    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, float('inf')):
            continue  # stale entry — đã tìm được đường ngắn hơn

        for v, weight in graph.get(u, []):
            new_dist = d + weight
            if new_dist < dist.get(v, float('inf')):
                dist[v] = new_dist
                heapq.heappush(heap, (new_dist, v))

    return dist

def network_delay_time(times: list[list[int]], n: int, k: int) -> int:
    """LeetCode 743. Dijkstra: thời gian để tất cả node nhận signal. O(E log V)."""
    graph = defaultdict(list)
    for u, v, w in times:
        graph[u].append((v, w))

    dist = dijkstra(graph, k)

    if len(dist) < n:
        return -1  # có node không thể reach
    return max(dist.values())
```

### Detect Cycle

```python
def has_cycle_undirected(graph: dict, n: int) -> bool:
    """Dùng Union-Find — O(E α(V))."""
    uf = UnionFind(n)
    for u in graph:
        for v in graph[u]:
            if u < v:  # tránh xử lý edge hai lần
                if not uf.union(u, v):
                    return True
    return False

def has_cycle_directed(graph: dict, n: int) -> bool:
    """DFS với 3 states: unvisited/in_progress/done. O(V+E)."""
    state = [0] * n  # 0=white, 1=gray, 2=black

    def dfs(node: int) -> bool:
        if state[node] == 1: return True   # back edge → cycle
        if state[node] == 2: return False  # already processed
        state[node] = 1
        for neighbor in graph.get(node, []):
            if dfs(neighbor):
                return True
        state[node] = 2
        return False

    return any(state[i] == 0 and dfs(i) for i in range(n))
```

---

## 10. Dynamic Programming

### Memoization vs Tabulation

```python
# Memoization — top-down, đệ quy + cache
# Ưu: dễ viết, chỉ tính subproblem cần thiết
# Nhược: call stack overhead, risk RecursionError
from functools import lru_cache

@lru_cache(maxsize=None)
def fib_memo(n: int) -> int:
    if n <= 1: return n
    return fib_memo(n-1) + fib_memo(n-2)

# Tabulation — bottom-up, iterative + table
# Ưu: không có call stack, thường nhanh hơn
# Nhược: phải xác định thứ tự tính toán
def fib_tab(n: int) -> int:
    if n <= 1: return n
    dp = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
    return dp[n]

# Space-optimized — chỉ giữ 2 giá trị cuối
def fib_optimized(n: int) -> int:
    if n <= 1: return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
```

### Cách nhận biết bài DP

- Hỏi về **tối ưu** (max/min) hoặc **đếm** số cách
- Bài có thể chia thành **overlapping subproblems**
- Có **optimal substructure**: solution của bài lớn phụ thuộc vào solution bài nhỏ
- Từ khóa: "minimum cost", "maximum profit", "number of ways", "longest/shortest"

### 1D DP Patterns

```python
def climb_stairs(n: int) -> int:
    """LeetCode 70. Số cách leo n bậc thang, mỗi lần 1 hoặc 2 bậc. O(n) O(1)."""
    if n <= 2: return n
    a, b = 1, 2
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b

def house_robber(nums: list[int]) -> int:
    """LeetCode 198. Không được lấy 2 nhà liên tiếp. O(n) O(1)."""
    # dp[i] = max tiền có thể lấy từ nhà 0 đến i
    # dp[i] = max(dp[i-1], dp[i-2] + nums[i])
    prev2, prev1 = 0, 0
    for num in nums:
        prev2, prev1 = prev1, max(prev1, prev2 + num)
    return prev1

def coin_change(coins: list[int], amount: int) -> int:
    """LeetCode 322. Số đồng xu tối thiểu. O(amount * len(coins)) O(amount)."""
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0  # base case: 0 đồng = 0 xu

    for a in range(1, amount + 1):
        for coin in coins:
            if coin <= a:
                dp[a] = min(dp[a], dp[a - coin] + 1)

    return dp[amount] if dp[amount] != float('inf') else -1

def coin_change_ways(coins: list[int], amount: int) -> int:
    """LeetCode 518. Đếm số CÁCH tạo amount (unbounded knapsack). O(amount * coins)."""
    dp = [0] * (amount + 1)
    dp[0] = 1  # 1 cách tạo amount=0: không dùng xu nào
    for coin in coins:
        for a in range(coin, amount + 1):
            dp[a] += dp[a - coin]
    return dp[amount]

def word_break(s: str, word_dict: list[str]) -> bool:
    """LeetCode 139. O(n² * m) với m = avg word length."""
    word_set = set(word_dict)
    dp = [False] * (len(s) + 1)
    dp[0] = True  # empty string luôn breakable

    for i in range(1, len(s) + 1):
        for j in range(i):
            if dp[j] and s[j:i] in word_set:
                dp[i] = True
                break
    return dp[len(s)]
```

### 2D DP Patterns

```python
def longest_common_subsequence(text1: str, text2: str) -> int:
    """LeetCode 1143. O(m*n) time O(m*n) space."""
    m, n = len(text1), len(text2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i-1] == text2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1   # ký tự match: extend LCS
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])  # bỏ ký tự nào tốt hơn?

    return dp[m][n]

def edit_distance(word1: str, word2: str) -> int:
    """LeetCode 72. Min operations (insert/delete/replace) để word1→word2. O(m*n)."""
    m, n = len(word1), len(word2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # Base cases
    for i in range(m + 1): dp[i][0] = i  # xóa i ký tự
    for j in range(n + 1): dp[0][j] = j  # insert j ký tự

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if word1[i-1] == word2[j-1]:
                dp[i][j] = dp[i-1][j-1]          # no operation needed
            else:
                dp[i][j] = 1 + min(
                    dp[i-1][j],    # delete từ word1
                    dp[i][j-1],    # insert vào word1
                    dp[i-1][j-1]   # replace
                )

    return dp[m][n]

def unique_paths(m: int, n: int) -> int:
    """LeetCode 62. Số đường đi từ góc trái trên đến góc phải dưới. O(m*n)."""
    dp = [[1] * n for _ in range(m)]
    for i in range(1, m):
        for j in range(1, n):
            dp[i][j] = dp[i-1][j] + dp[i][j-1]
    return dp[m-1][n-1]
```

### 0/1 Knapsack Pattern

```python
def knapsack_01(weights: list[int], values: list[int], capacity: int) -> int:
    """
    Knapsack 0/1: mỗi item chỉ dùng 1 lần.
    O(n * capacity) time O(n * capacity) space.
    """
    n = len(weights)
    # dp[i][w] = max value dùng item 0..i-1 với sức chứa w
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        w, v = weights[i-1], values[i-1]
        for cap in range(capacity + 1):
            dp[i][cap] = dp[i-1][cap]  # không lấy item i
            if cap >= w:
                dp[i][cap] = max(dp[i][cap], dp[i-1][cap - w] + v)  # lấy item i

    return dp[n][capacity]

def knapsack_01_optimized(weights: list[int], values: list[int], capacity: int) -> int:
    """O(capacity) space — chỉ dùng 1D dp, iterate capacity ngược."""
    dp = [0] * (capacity + 1)

    for w, v in zip(weights, values):
        for cap in range(capacity, w - 1, -1):  # ngược từ capacity về w
            dp[cap] = max(dp[cap], dp[cap - w] + v)

    return dp[capacity]
```

### Interval DP

```python
def burst_balloons(nums: list[int]) -> int:
    """LeetCode 312. O(n³). Interval DP: dp[i][j] = max coins burst tất cả balloon giữa i và j."""
    nums = [1] + nums + [1]  # padding
    n = len(nums)
    dp = [[0] * n for _ in range(n)]

    for length in range(2, n):          # length của interval
        for left in range(0, n - length):
            right = left + length
            for k in range(left + 1, right):  # k: balloon bị burst CUỐI CÙNG trong [left, right]
                dp[left][right] = max(
                    dp[left][right],
                    dp[left][k] + nums[left] * nums[k] * nums[right] + dp[k][right]
                )

    return dp[0][n - 1]

def matrix_chain_multiplication(dims: list[int]) -> int:
    """Số phép nhân tối thiểu để nhân chuỗi ma trận. O(n³)."""
    n = len(dims) - 1  # số ma trận
    dp = [[0] * n for _ in range(n)]

    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            dp[i][j] = float('inf')
            for k in range(i, j):
                cost = dp[i][k] + dp[k+1][j] + dims[i] * dims[k+1] * dims[j+1]
                dp[i][j] = min(dp[i][j], cost)

    return dp[0][n-1]
```

---

## 11. Sorting & Searching

### Quick Sort

```python
def quicksort(arr: list[int], lo: int = 0, hi: int = None) -> None:
    """
    O(n log n) average, O(n²) worst (sorted input).
    O(log n) space average (call stack).
    In-place.
    """
    if hi is None:
        hi = len(arr) - 1

    if lo >= hi:
        return

    pivot_idx = partition(arr, lo, hi)
    quicksort(arr, lo, pivot_idx - 1)
    quicksort(arr, pivot_idx + 1, hi)

def partition(arr: list[int], lo: int, hi: int) -> int:
    """Lomuto partition scheme."""
    pivot = arr[hi]
    i = lo - 1  # i: boundary của phần nhỏ hơn pivot

    for j in range(lo, hi):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]

    arr[i+1], arr[hi] = arr[hi], arr[i+1]  # đặt pivot vào đúng vị trí
    return i + 1
```

### Merge Sort

```python
def mergesort(arr: list[int]) -> list[int]:
    """
    O(n log n) — guaranteed mọi case.
    O(n) space.
    Stable sort.
    """
    if len(arr) <= 1:
        return arr

    mid = len(arr) // 2
    left = mergesort(arr[:mid])
    right = mergesort(arr[mid:])
    return merge(left, right)

def merge(left: list[int], right: list[int]) -> list[int]:
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

def count_inversions(arr: list[int]) -> int:
    """Đếm số cặp (i,j) có i<j nhưng arr[i]>arr[j] — dùng merge sort. O(n log n)."""
    count = [0]

    def merge_count(left: list[int], right: list[int]) -> list[int]:
        result = []
        i = j = 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                count[0] += len(left) - i  # tất cả left[i:] đều lớn hơn right[j]
                j += 1
        result.extend(left[i:])
        result.extend(right[j:])
        return result

    def sort_count(arr: list[int]) -> list[int]:
        if len(arr) <= 1:
            return arr
        mid = len(arr) // 2
        return merge_count(sort_count(arr[:mid]), sort_count(arr[mid:]))

    sort_count(arr)
    return count[0]
```

### Binary Search Variants

```python
def binary_search_standard(arr: list[int], target: int) -> int:
    """Tìm bất kỳ vị trí nào có target. O(log n)."""
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1

def find_first_occurrence(arr: list[int], target: int) -> int:
    """Tìm vị trí đầu tiên của target. O(log n)."""
    lo, hi = 0, len(arr) - 1
    result = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            result = mid
            hi = mid - 1   # tiếp tục tìm bên trái
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return result

def find_last_occurrence(arr: list[int], target: int) -> int:
    """Tìm vị trí cuối cùng của target. O(log n)."""
    lo, hi = 0, len(arr) - 1
    result = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            result = mid
            lo = mid + 1   # tiếp tục tìm bên phải
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return result

def search_rotated_array(nums: list[int], target: int) -> int:
    """LeetCode 33. O(log n). Array đã được rotated."""
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        # Xác định nửa nào đang sorted
        if nums[lo] <= nums[mid]:          # nửa trái sorted
            if nums[lo] <= target < nums[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:                              # nửa phải sorted
            if nums[mid] < target <= nums[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1

def find_min_rotated(nums: list[int]) -> int:
    """LeetCode 153. Tìm minimum trong rotated sorted array. O(log n)."""
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] > nums[hi]:
            lo = mid + 1  # min nằm bên phải
        else:
            hi = mid      # min nằm bên trái hoặc tại mid
    return nums[lo]
```

### Dutch National Flag — 3-Way Partition

```python
def sort_colors(nums: list[int]) -> None:
    """LeetCode 75. Sort [0,1,2] in-place. O(n) O(1)."""
    low = 0           # boundary của vùng 0s
    mid = 0           # current pointer
    high = len(nums) - 1  # boundary của vùng 2s

    while mid <= high:
        if nums[mid] == 0:
            nums[low], nums[mid] = nums[mid], nums[low]
            low += 1
            mid += 1
        elif nums[mid] == 1:
            mid += 1    # 1 đúng chỗ rồi
        else:           # nums[mid] == 2
            nums[mid], nums[high] = nums[high], nums[mid]
            high -= 1   # KHÔNG tăng mid vì phần tử mới chưa được xét
```

---

## 12. String Algorithms

### KMP Pattern Matching

```python
def build_lps(pattern: str) -> list[int]:
    """
    LPS (Longest Proper Prefix which is also Suffix) array.
    lps[i] = độ dài của longest proper prefix của pattern[:i+1] = suffix.
    O(m) với m = len(pattern).
    """
    m = len(pattern)
    lps = [0] * m
    length = 0   # độ dài của current matching prefix-suffix
    i = 1

    while i < m:
        if pattern[i] == pattern[length]:
            length += 1
            lps[i] = length
            i += 1
        elif length > 0:
            length = lps[length - 1]  # fallback — không reset i!
        else:
            lps[i] = 0
            i += 1

    return lps

def kmp_search(text: str, pattern: str) -> list[int]:
    """
    KMP: tìm tất cả vị trí pattern trong text. O(n+m).
    n = len(text), m = len(pattern).
    """
    n, m = len(text), len(pattern)
    lps = build_lps(pattern)
    matches = []

    i = j = 0  # i: index trong text, j: index trong pattern
    while i < n:
        if text[i] == pattern[j]:
            i += 1
            j += 1
            if j == m:
                matches.append(i - j)   # tìm thấy match
                j = lps[j - 1]          # tiếp tục tìm match tiếp theo
        elif j > 0:
            j = lps[j - 1]  # fallback: không reset i
        else:
            i += 1

    return matches

# Ứng dụng: repeated substring pattern
def repeated_substring_pattern(s: str) -> bool:
    """LeetCode 459. Dùng KMP. O(n)."""
    # Trick: nếu s được tạo bởi repeating substring,
    # thì s là substring của (s+s)[1:-1]
    doubled = (s + s)[1:-1]
    return s in doubled  # Python dùng optimized search
```

### Sliding Window cho Substring Problems

```python
def longest_substring_k_distinct(s: str, k: int) -> int:
    """Substring dài nhất với tối đa k distinct characters. O(n)."""
    from collections import defaultdict
    char_count = defaultdict(int)
    left = 0
    max_len = 0

    for right in range(len(s)):
        char_count[s[right]] += 1

        while len(char_count) > k:
            char_count[s[left]] -= 1
            if char_count[s[left]] == 0:
                del char_count[s[left]]
            left += 1

        max_len = max(max_len, right - left + 1)

    return max_len

def longest_repeating_char_replacement(s: str, k: int) -> int:
    """LeetCode 424. Thay tối đa k ký tự để longest substring chỉ có 1 loại. O(n)."""
    count = {}
    left = 0
    max_count = 0   # count của ký tự phổ biến nhất trong cửa sổ

    for right in range(len(s)):
        count[s[right]] = count.get(s[right], 0) + 1
        max_count = max(max_count, count[s[right]])

        # window size - max_count = số ký tự cần thay
        window_size = right - left + 1
        if window_size - max_count > k:
            count[s[left]] -= 1
            left += 1  # co cửa sổ

    return len(s) - left  # kích thước cửa sổ cuối
```

### Palindrome Tricks

```python
def is_palindrome(s: str) -> bool:
    """O(n) O(1)."""
    lo, hi = 0, len(s) - 1
    while lo < hi:
        if s[lo] != s[hi]:
            return False
        lo += 1
        hi -= 1
    return True

def longest_palindromic_substring(s: str) -> str:
    """LeetCode 5. Expand around center. O(n²) O(1)."""
    best = ""

    def expand(lo: int, hi: int) -> str:
        while lo >= 0 and hi < len(s) and s[lo] == s[hi]:
            lo -= 1
            hi += 1
        return s[lo+1:hi]  # s[lo+1..hi-1] là palindrome lớn nhất

    for i in range(len(s)):
        # Odd length palindrome: center tại i
        p1 = expand(i, i)
        # Even length palindrome: center giữa i và i+1
        p2 = expand(i, i + 1)
        if len(p1) > len(best): best = p1
        if len(p2) > len(best): best = p2

    return best

def count_palindromic_substrings(s: str) -> int:
    """LeetCode 647. O(n²) O(1)."""
    count = 0

    def expand_count(lo: int, hi: int) -> int:
        c = 0
        while lo >= 0 and hi < len(s) and s[lo] == s[hi]:
            c += 1
            lo -= 1
            hi += 1
        return c

    for i in range(len(s)):
        count += expand_count(i, i)      # odd
        count += expand_count(i, i + 1)  # even

    return count
```

### String Hashing — Rabin-Karp

```python
def rabin_karp(text: str, pattern: str) -> list[int]:
    """
    Rolling hash: tìm pattern trong text. O(n+m) average, O(n*m) worst.
    Thực tế ít bị worst case nếu chọn hash tốt.
    """
    n, m = len(text), len(pattern)
    if m > n:
        return []

    BASE = 31
    MOD = 10**9 + 7

    def hash_str(s: str, length: int) -> int:
        h = 0
        for i in range(length):
            h = (h * BASE + ord(s[i]) - ord('a') + 1) % MOD
        return h

    pattern_hash = hash_str(pattern, m)
    window_hash = hash_str(text, m)

    # BASE^(m-1) % MOD — dùng để remove ký tự đầu
    power = pow(BASE, m - 1, MOD)

    matches = []
    if window_hash == pattern_hash and text[:m] == pattern:
        matches.append(0)

    for i in range(1, n - m + 1):
        # Rolling: remove text[i-1], add text[i+m-1]
        window_hash = (window_hash - (ord(text[i-1]) - ord('a') + 1) * power) % MOD
        window_hash = (window_hash * BASE + ord(text[i+m-1]) - ord('a') + 1) % MOD
        window_hash = (window_hash + MOD) % MOD  # đảm bảo dương

        if window_hash == pattern_hash and text[i:i+m] == pattern:
            matches.append(i)

    return matches
```

---

## 13. Interview Quick Reference

### Bảng Complexity của Data Structures

| Data Structure | Access | Search | Insert | Delete | Space |
|---------------|--------|--------|--------|--------|-------|
| Array | O(1) | O(n) | O(n) | O(n) | O(n) |
| Sorted Array | O(1) | O(log n) | O(n) | O(n) | O(n) |
| Linked List | O(n) | O(n) | O(1)* | O(1)* | O(n) |
| Hash Map | O(1)** | O(1)** | O(1)** | O(1)** | O(n) |
| Stack | O(n) | O(n) | O(1) | O(1) | O(n) |
| Queue | O(n) | O(n) | O(1) | O(1) | O(n) |
| Binary Heap | O(1) top | O(n) | O(log n) | O(log n) | O(n) |
| BST (balanced) | O(log n) | O(log n) | O(log n) | O(log n) | O(n) |
| Trie | - | O(k) | O(k) | O(k) | O(n*k) |

*khi đã có pointer, **average case

### Bảng Sorting Algorithms

| Algorithm | Best | Average | Worst | Space | Stable |
|-----------|------|---------|-------|-------|--------|
| Bubble Sort | O(n) | O(n²) | O(n²) | O(1) | Yes |
| Quick Sort | O(n log n) | O(n log n) | O(n²) | O(log n) | No |
| Merge Sort | O(n log n) | O(n log n) | O(n log n) | O(n) | Yes |
| Heap Sort | O(n log n) | O(n log n) | O(n log n) | O(1) | No |
| Counting Sort | O(n+k) | O(n+k) | O(n+k) | O(k) | Yes |
| Python `sort()` | O(n) | O(n log n) | O(n log n) | O(n) | Yes |

### Cheat Sheet — Khi nào dùng Data Structure nào

```
Cần lookup nhanh theo key       → HashMap / HashSet
Cần tìm min/max liên tục        → Heap (heapq)
Cần dữ liệu sorted + dynamic   → Sorted List (sortedcontainers)
Cần LIFO / undo / parse expr    → Stack
Cần FIFO / BFS                  → deque
Cần range queries               → Prefix Sum / Segment Tree
Cần khoảng cách ngắn nhất       → Dijkstra (weighted) / BFS (unweighted)
Cần detect cycle                → Union-Find / DFS
Cần topo order                  → Topo Sort (Kahn's / DFS)
Cần top K                       → Heap kích thước K
Cần substring search            → Sliding Window / KMP
Cần tối ưu / đếm số cách       → Dynamic Programming
Cần backtracking                → DFS + undo
```

### Common Mistakes và Cách Tránh

**1. Off-by-one trong binary search**
```python
# WRONG: lo < hi có thể bỏ lỡ phần tử cuối
while lo < hi:  # lỗi khi 1 phần tử

# RIGHT: lo <= hi
while lo <= hi:
    mid = lo + (hi - lo) // 2   # tránh overflow (dù Python không overflow)
```

**2. Không reset visited trong DFS**
```python
# WRONG: dùng chung visited cho nhiều lần gọi
visited = set()
def dfs(node):
    visited.add(node)  # lỗi: visited không được reset giữa các calls

# RIGHT: truyền visited vào hoặc reset trước mỗi query
def dfs(node, visited=None):
    if visited is None:
        visited = set()
    visited.add(node)
```

**3. Stack overflow với đệ quy sâu**
```python
import sys
sys.setrecursionlimit(100000)   # tăng limit nếu cần

# Hoặc dùng iterative với explicit stack
```

**4. Quên xử lý edge cases**
```python
# Luôn check:
# - Input rỗng (empty list/string)
# - Input có 1 phần tử
# - Tất cả phần tử giống nhau
# - Negative numbers (khi nói đến sum/product)
# - None/null nodes trong tree
```

**5. Modify list trong khi iterate**
```python
# WRONG
for i, x in enumerate(nums):
    if x == 0:
        nums.pop(i)  # skip phần tử tiếp theo!

# RIGHT: dùng two pointer hoặc tạo list mới
nums = [x for x in nums if x != 0]
```

**6. Integer overflow trong các ngôn ngữ khác (Python OK)**
```python
# Python int không overflow, nhưng trong Java/C++:
# mid = lo + (hi - lo) // 2  thay vì (lo + hi) // 2
```

### WorldQuant-Style Problem-Solving Approach

WorldQuant interview thường focus vào bài toán về dữ liệu tài chính, time series, và tối ưu hóa. Quy trình giải bài hiệu quả:

**Bước 1 — Clarify (1-2 phút)**
- "Input là gì? Sorted không? Có thể negative không?"
- "Tìm bất kỳ đáp án hay tất cả đáp án?"
- "Constraints: n bao nhiêu? Memory giới hạn bao nhiêu?"

**Bước 2 — Brute force trước**
- Nói ra brute force và complexity của nó
- "Brute force O(n²) — có thể tối ưu không?"

**Bước 3 — Nhận biết pattern**
```
Sorted array + tìm pair     → Two Pointer
Subarray liên tiếp          → Sliding Window
Tìm k phần tử lớn nhất     → Min Heap size k
Có overlapping subproblems  → DP
Tìm đường ngắn nhất         → BFS/Dijkstra
Permutation/combination     → Backtracking
```

**Bước 4 — Code có cấu trúc**
```python
def solve(input_data):
    # 1. Edge cases
    if not input_data:
        return default_value

    # 2. Khởi tạo
    ...

    # 3. Main logic (có comment)
    ...

    # 4. Return
    return result
```

**Bước 5 — Test với examples**
```python
# Luôn test bằng tay với ít nhất 2-3 cases:
# - Normal case (ví dụ trong đề)
# - Edge case (empty, single element, all same)
# - Corner case (negative numbers, very large input)
```

**Bước 6 — Nói về improvements**
- "Có thể tối ưu space từ O(n) xuống O(1) không?"
- "Nếu data stream (không biết trước n)?"
- "Nếu cần parallel execution?"

---

*Tổng hợp: File này cover đầy đủ DSA cho phỏng vấn từ Easy đến Hard. Ôn theo thứ tự: Big-O → Arrays → HashMap → Stack/Queue → Linked List → Trees → Graphs → DP. Mỗi section có template tái dùng được — hãy nhớ template, không nhớ từng bài cụ thể.*
