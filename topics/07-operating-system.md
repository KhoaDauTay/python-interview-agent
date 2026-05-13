# Operating System — Question Bank
> Nguồn: cs_questions.txt — OPERATING SYSTEM section

---

## EASY

### OS-E01: Process vs Thread
**Câu hỏi:** Process và Thread khác nhau thế nào? Tại sao Thread được gọi là "lightweight process"?
**Keywords:** address space, stack, heap, shared memory, context switch, PCB, TLS
**Expected answer:**
| | Process | Thread |
|--|---------|--------|
| Memory | Riêng (address space độc lập) | Share heap với các thread cùng process |
| Stack | Riêng | Riêng |
| Context switch | Chậm (thay đổi page table) | Nhanh hơn |
| Communication | IPC (pipe, socket, shared memory) | Shared memory trực tiếp |
**Follow-up:** "Python GIL ảnh hưởng gì đến threading? Khi nào dùng multiprocessing thay vì threading?"

### OS-E02: Concurrency vs Parallelism
**Câu hỏi:** Concurrency và Parallelism khác nhau thế nào? Cho ví dụ.
**Keywords:** interleaving, simultaneous, single core vs multi core, async vs parallel
**Expected answer:**
- **Concurrency**: Nhiều task "in progress" cùng lúc, có thể trên 1 core (interleaving). Ví dụ: asyncio event loop.
- **Parallelism**: Nhiều task thực sự chạy đồng thời trên nhiều cores. Ví dụ: multiprocessing.
**Follow-up:** "FastAPI async hoạt động là concurrency hay parallelism?"

### OS-E03: Stack vs Heap
**Câu hỏi:** Stack space và Heap space khác nhau thế nào? Cái gì được lưu ở đâu?
**Keywords:** stack frame, local variables, LIFO, dynamic allocation, fragmentation, GC
**Expected answer:**
- **Stack**: Local variables, function parameters, return address. LIFO, tự động deallocate khi function return. Giới hạn size → stack overflow.
- **Heap**: Dynamic allocation (`malloc`, `new`, Python objects). Manual/GC deallocate. Lớn hơn nhưng chậm hơn.
**Follow-up:** "Stack overflow xảy ra khi nào? Recursion sâu có thể gây ra không?"

---

## MEDIUM

### OS-M01: Race condition & Locking
**Câu hỏi:** Race condition là gì? Mutex, Semaphore, Spinlock khác nhau thế nào?
**Keywords:** critical section, atomic operation, mutex (binary semaphore), counting semaphore, busy-wait
**Expected answer:**
- **Race condition**: 2 threads cùng read/write shared data → kết quả không xác định
- **Mutex**: Binary lock, chỉ 1 thread vào critical section. Thread bị block khi lock unavailable.
- **Semaphore**: Counter, cho phép N threads vào. Dùng để giới hạn concurrent access (e.g., connection pool).
- **Spinlock**: Busy-wait (không sleep) → tốt cho lock ngắn, xấu cho lock dài.
**CV link:** "Celery Beat duplicate runs bug ở Sidecardata — đây là race condition không? Fix bằng distributed lock (Redis) như thế nào?"
**Follow-up:** "Deadlock xảy ra khi nào? 4 điều kiện của deadlock (Coffman conditions)?"

### OS-M02: Deadlock
**Câu hỏi:** Deadlock là gì? 4 điều kiện cần để deadlock xảy ra? Cách tránh?
**Keywords:** mutual exclusion, hold and wait, no preemption, circular wait, lock ordering, timeout
**Expected answer:** 4 điều kiện Coffman:
1. **Mutual exclusion**: Resource chỉ 1 thread dùng tại 1 thời điểm
2. **Hold and wait**: Thread giữ resource A và chờ resource B
3. **No preemption**: Resource không bị lấy lại forcefully
4. **Circular wait**: T1 chờ T2, T2 chờ T1
**Prevention**: Lock ordering (luôn acquire theo thứ tự), timeout, trylock.
**Follow-up:** "Database deadlock detect thế nào? PostgreSQL xử lý deadlock ra sao?"

### OS-M03: Virtual Memory & Paging
**Câu hỏi:** Virtual memory là gì? Tại sao cần nó? Paging hoạt động thế nào?
**Keywords:** page table, MMU, physical vs virtual address, page fault, swap space, TLB
**Expected answer:** Virtual memory cho mỗi process "tưởng" mình có toàn bộ address space riêng → isolation, security. MMU translate virtual→physical address qua page table. Page fault khi page không có trong RAM → load từ disk (swap).
**Follow-up:** "2 processes có thể map cùng physical address không? Khi nào? (shared libraries, mmap, copy-on-write)"

### OS-M04: Context Switch
**Câu hỏi:** Context switch là gì? CPU switch giữa processes/threads thế nào? Chi phí là gì?
**Keywords:** PCB, registers save/restore, TLB flush, scheduling, preemptive vs cooperative
**Expected answer:** OS save CPU registers + program counter vào PCB, load registers của process mới. TLB flush khi switch process (expensive). Thread switch trong cùng process không flush TLB.
**Follow-up:** "Async/await (coroutines) và context switch khác gì? Tại sao async nhanh hơn threading cho I/O-bound?"

### OS-M05: Garbage Collection
**Câu hỏi:** Garbage Collection hoạt động thế nào trong Python? Khi nào được trigger?
**Keywords:** reference counting, cyclic GC, `gc` module, `__del__`, generational GC, stop-the-world
**Expected answer:**
1. **Reference counting**: Mỗi object có counter. Counter = 0 → deallocate ngay lập tức.
2. **Cyclic GC**: Reference counting không detect circular references → Python có `gc` module chạy định kỳ để collect cycles.
3. **Trigger**: Khi allocation count vượt threshold theo từng generation (gen 0, 1, 2).
**Follow-up:** "Memory leak trong long-running Python service xảy ra thế nào? Làm sao detect?"

---

## HARD

### OS-H01: Copy-on-Write (COW)
**Câu hỏi:** Copy-on-Write là gì? Tại sao `fork()` dùng COW? Ảnh hưởng gì đến Redis/Celery?
**Keywords:** `fork()`, page sharing, page fault on write, Redis BGSAVE, memory spike
**Expected answer:** Khi `fork()`, child process share cùng physical pages với parent. Chỉ khi một process write → page mới được copy. Tiết kiệm memory.
**Redis BGSAVE**: Fork để snapshot. Nếu nhiều write sau fork → nhiều COW copies → memory spike.
**Celery**: Worker spawn bằng `fork()` → shared memory với parent (preloaded models, connections).
**Follow-up:** "Tại sao Celery recommend `--pool=prefork` cho CPU-bound và `--pool=gevent` cho I/O-bound?"

### OS-H02: File Descriptor & "Everything is a file"
**Câu hỏi:** Tại sao Linux nói "everything is a file"? File descriptor là gì?
**Keywords:** FD (integer), VFS, stdin/stdout/stderr (0/1/2), socket FD, pipe, `ulimit`
**Expected answer:** Linux abstract mọi I/O resource (network socket, pipe, device) thành file → uniform API (`read()`, `write()`, `close()`). FD là integer index vào file descriptor table của process.
**Follow-up:** "Maximum FD của một process là bao nhiêu? (`ulimit -n`). Production server cần tune gì?"

### OS-H03: System Call
**Câu hỏi:** System call là gì? Điều gì xảy ra với CPU khi execute syscall? User space vs kernel space?
**Keywords:** trap/interrupt, privilege level (ring 0/3), context switch to kernel, `strace`
**Expected answer:** Syscall là API để user-space program request kernel services (read file, network, memory alloc). CPU switch từ ring 3 (user) → ring 0 (kernel) via software interrupt → execute kernel code → return.
**Follow-up:** "Tại sao syscall tốn kém? Làm sao minimize syscalls trong high-performance code? (batch reads, `mmap`)"
