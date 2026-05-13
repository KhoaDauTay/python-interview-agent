# Two Sum

**Difficulty:** Easy  
**Topic:** Array, Hash Map, Two Pointers  
**Source:** LeetCode #1

---

## Problem

Given an array of integers `nums` and an integer `target`, return the indices `i` and `j` such that `nums[i] + nums[j] == target` and `i != j`.

Return the answer with the smaller index first.

**Constraints:**
- `2 <= nums.length <= 1000`
- `-10,000,000 <= nums[i] <= 10,000,000`
- Only one valid answer exists.

---

## Approach

### Brute Force — O(n²) time, O(1) space

Duyệt mọi cặp `(i, j)`, kiểm tra tổng. Đơn giản nhưng chậm.

```python
def twoSum(nums: list[int], target: int) -> list[int]:
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
```

---

### Optimal — Hash Map — O(n) time, O(n) space

Với mỗi phần tử `x`, kiểm tra xem `target - x` đã xuất hiện trước đó chưa bằng hash map.

```python
def twoSum(nums: list[int], target: int) -> list[int]:
    seen = {}  # value -> index
    for i, x in enumerate(nums):
        complement = target - x
        if complement in seen:
            return [seen[complement], i]
        seen[x] = i
```

**Tại sao đúng:**
- `seen[complement]` luôn có index nhỏ hơn `i` (vì ta chỉ lưu các phần tử đã đi qua).
- Nên kết quả tự động trả về `[index nhỏ, index lớn]`.

---

### Two Pointers — O(n log n) time, O(n) space

Two pointers chỉ hoạt động trên **mảng đã sắp xếp**. Với bài gốc (unsorted), ta sort kèm index gốc, rồi dùng left/right pointer thu hẹp dần.

```python
def twoSum(nums: list[int], target: int) -> list[int]:
    sorted_nums = sorted(enumerate(nums), key=lambda x: x[1])
    left, right = 0, len(sorted_nums) - 1

    while left < right:
        current_sum = sorted_nums[left][1] + sorted_nums[right][1]
        if current_sum == target:
            i, j = sorted_nums[left][0], sorted_nums[right][0]
            return [min(i, j), max(i, j)]
        elif current_sum < target:
            left += 1
        else:
            right -= 1
```

**Tại sao đúng:**
- Nếu tổng < target → cần số lớn hơn → tăng `left`
- Nếu tổng > target → cần số nhỏ hơn → giảm `right`
- Index gốc được giữ lại qua `enumerate` trước khi sort.

**Khi nào dùng:** input đã sorted sẵn (LeetCode #167) thì Two Pointers tối ưu hơn Hash Map vì O(1) space. Với bài gốc unsorted thì Hash Map vẫn là lựa chọn tốt hơn.

---

## Walkthrough — Example

```
nums = [3, 4, 5, 6], target = 7

i=0, x=3: complement=4, not in seen → seen={3:0}
i=1, x=4: complement=3, found at seen[3]=0 → return [0, 1] ✓
```

---

## Complexity

| Approach     | Time  | Space |
|--------------|-------|-------|
| Brute Force  | O(n²)    | O(1)  |
| Hash Map     | O(n)     | O(n)  |
| Two Pointers | O(n log n) | O(n)  | ← sort + giữ index gốc |

---

## Key Insight

> Thay vì hỏi *"có cặp nào tổng = target không?"*, hỏi lại *"với x hiện tại, complement của nó có ở đâu đó trước đó không?"* → tra bảng O(1) thay vì duyệt O(n).

---

## Similar Problems

- Three Sum (LeetCode #15) — mở rộng tìm 3 số
- Two Sum II - Input Array Is Sorted (LeetCode #167) — dùng two pointers thay hash map
