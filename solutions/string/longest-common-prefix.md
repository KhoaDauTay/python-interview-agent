# Longest Common Prefix

**Difficulty:** Easy  
**Topic:** String  
**Source:** LeetCode #14

---

## Problem

Given an array of strings `strs`, return the longest common prefix of all strings. If none exists, return `""`.

---

## Approach

### Vertical Scanning — O(n·m) time, O(1) space

Duyệt từng ký tự theo chiều dọc (cùng vị trí trên tất cả string). Dừng ngay khi có string nào không khớp hoặc đã hết độ dài.

```python
def longestCommonPrefix(strs: list[str]) -> str:
    for i in range(len(strs[0])):
        for s in strs[1:]:
            if i == len(s) or s[i] != strs[0][i]:
                return strs[0][:i]
    return strs[0]
```

**Tại sao đúng:**
- Lấy `strs[0]` làm chuẩn, duyệt từng vị trí `i`.
- Với mỗi `i`, kiểm tra tất cả string còn lại có cùng ký tự đó không.
- Dừng sớm ngay khi phát hiện không khớp → không duyệt thừa.

---

### Sort + So sánh đầu-cuối — O(n log n) time, O(1) space

Sau khi sort, prefix chung của **toàn bộ** mảng chính là prefix chung của string **nhỏ nhất** và **lớn nhất** (theo thứ tự từ điển).

```python
def longestCommonPrefix(strs: list[str]) -> str:
    strs.sort()
    first, last = strs[0], strs[-1]
    i = 0
    while i < len(first) and i < len(last) and first[i] == last[i]:
        i += 1
    return first[:i]
```

**Tại sao đúng:**
- Sau sort, `first` và `last` là hai string "xa nhau nhất" về mặt ký tự.
- Nếu hai đầu cực này còn chung prefix thì tất cả string ở giữa cũng chung prefix đó.
- Chỉ cần so sánh 2 string thay vì n string.

---

## Walkthrough — Example

```
strs = ["bat", "bag", "bank", "band"], target prefix = "ba"

Vertical Scanning:
i=0: b==b==b==b ✓
i=1: a==a==a==a ✓
i=2: t vs g → không khớp → return strs[0][:2] = "ba" ✓

Sort + So sánh:
sorted = ["bag", "band", "bank", "bat"]
first="bag", last="bat"
i=0: b==b ✓
i=1: a==a ✓
i=2: g vs t → dừng → return "ba" ✓
```

---

## Complexity

| Approach            | Time     | Space |
|---------------------|----------|-------|
| Vertical Scanning   | O(n·m)   | O(1)  |
| Sort + Compare      | O(n log n) | O(1) |

`n` = số string, `m` = độ dài string ngắn nhất.

> Vertical Scanning thường nhanh hơn trong thực tế vì dừng sớm ngay khi không khớp.

---

## Key Insight

> Không cần so sánh tất cả các cặp. Chỉ cần tìm điểm **bất đồng đầu tiên** — hoặc duyệt thẳng đứng theo cột, hoặc sort rồi chỉ so 2 đầu cực.

---

## Edge Cases

- `strs = ["a"]` → return `"a"`
- `strs = ["", "abc"]` → return `""`
- `strs = ["abc", "abc"]` → return `"abc"`

---

## Similar Problems

- Longest Common Subsequence (LeetCode #1143) — khó hơn, dùng DP
