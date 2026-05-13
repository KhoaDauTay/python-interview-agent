# Networking — Question Bank
> Nguồn: cs_questions.txt — NETWORKING section

---

## EASY

### NET-E01: TCP vs UDP
**Câu hỏi:** Sự khác biệt giữa TCP và UDP là gì? Khi nào dùng TCP, khi nào dùng UDP?
**Keywords:** reliable/unreliable, ordered, connection-oriented, handshake, checksum, latency
**Expected answer:**
| | TCP | UDP |
|--|-----|-----|
| Reliable | ✅ có ACK | ❌ fire-and-forget |
| Ordered | ✅ | ❌ |
| Speed | Chậm hơn | Nhanh hơn |
| Use case | HTTP, DB, file transfer | DNS, video streaming, gaming |
**Follow-up:** "Tại sao DNS dùng UDP thay vì TCP?"

### NET-E02: HTTP stateless
**Câu hỏi:** HTTP là stateless nghĩa là gì? Tại sao người ta thiết kế nó stateless?
**Keywords:** stateless, cookie, session, scalability, server independence
**Expected answer:** Mỗi request độc lập, server không nhớ request trước → dễ scale (bất kỳ server nào cũng handle được). State lưu ở client (cookie) hoặc server-side session store (Redis).
**Follow-up:** "Cookie bị đánh cắp thì sao? Làm thế nào để mitigate?"

### NET-E03: HTTP methods & status codes
**Câu hỏi:** REST/RESTful là gì? Phân biệt GET, POST, PUT, PATCH, DELETE.
**Keywords:** idempotent, safe, resource-based, stateless, HATEOAS
**Follow-up:** "GET có body không? Tại sao không nên dùng GET để thay đổi data?"

---

## MEDIUM

### NET-M01: TCP 3-way handshake
**Câu hỏi:** TCP mở connection như thế nào? Tại sao cần 3-way handshake chứ không phải 2-way?
**Keywords:** SYN, SYN-ACK, ACK, ISN (Initial Sequence Number), half-open connection
**Expected answer:**
```
Client → Server: SYN (seq=x)
Server → Client: SYN-ACK (seq=y, ack=x+1)
Client → Server: ACK (ack=y+1)
```
**Tại sao 3-way?** 2-way chỉ confirm client→server. Server cần biết client có nhận được SYN-ACK không → cần ACK thứ 3.
**Follow-up:** "Nếu handshake thứ 3 (ACK) bị mất, server làm gì? → SYN flood attack là gì?"

### NET-M02: TCP connection handling
**Câu hỏi:** TCP xử lý packet loss, timeout, và flow control như thế nào?
**Keywords:** retransmission, sliding window, congestion control, ACK, checksum, RTT
**Expected answer:**
- **Packet loss**: Timeout → retransmit. Duplicate ACK 3 lần → fast retransmit
- **Error detection**: Checksum trên mỗi segment
- **Flow control**: Sliding window — receiver báo `window size` (buffer còn bao nhiêu)
- **Congestion control**: Slow start → congestion avoidance (AIMD)
**Follow-up:** "Tại sao TCP có thể gây head-of-line blocking? HTTP/2 và HTTP/3 giải quyết thế nào?"

### NET-M03: DNS lookup
**Câu hỏi:** Khi gõ "google.com" vào browser, DNS lookup xảy ra thế nào? DNS dùng protocol gì?
**Keywords:** DNS cache (browser → OS → router → ISP), recursive vs iterative, UDP port 53, TTL
**Expected answer:**
1. Browser cache → OS cache (`/etc/hosts`) → Router cache → ISP DNS → Root nameserver → TLD → Authoritative DNS
2. DNS dùng **UDP** (nhanh, query nhỏ). TCP khi response > 512 bytes (zone transfer)
**Follow-up:** "DNS TTL là gì? Nếu thay đổi IP của server, phải chờ bao lâu để DNS propagate?"

### NET-M04: HTTPS & TLS
**Câu hỏi:** HTTPS hoạt động thế nào? TLS handshake gồm những bước gì?
**Keywords:** TLS handshake, certificate, CA, symmetric/asymmetric encryption, session key
**Expected answer:**
1. Client → Server: `ClientHello` (cipher suites, random)
2. Server → Client: Certificate + `ServerHello`
3. Client verify certificate với CA
4. Client generate session key (dùng server public key encrypt)
5. Cả hai dùng symmetric key để encrypt data
**Follow-up:** "Tại sao dùng asymmetric để trao đổi key, rồi dùng symmetric để transfer data?"

### NET-M05: Connection Pool
**Câu hỏi:** Connection pool là gì? Ưu nhược điểm? Tại sao FastAPI/Django cần nó?
**Keywords:** pool size, max overflow, TCP connection overhead, 3-way handshake cost, asyncpg, PgBouncer
**Expected answer:** Tạo sẵn N connections, reuse thay vì tạo mới mỗi request → tránh overhead của TCP handshake + TLS + DB auth.
**Disadvantage:** Memory footprint, idle connections, pool exhaustion.
**Follow-up:** "Pool size = bao nhiêu là optimal? Công thức tính?"

---

## HARD

### NET-H01: Socket & multiplexing
**Câu hỏi:** Socket là gì? Tại sao một server có thể handle nhiều connections trên cùng 1 port?
**Keywords:** 4-tuple (src IP, src port, dst IP, dst port), file descriptor, `accept()`, epoll/select
**Expected answer:** Port chỉ là phần của 4-tuple. Mỗi connection được identify bởi (client IP, client port, server IP, server port) → unique connection. OS dùng epoll/kqueue để multiplex.
**Follow-up:** "Maximum connections một server có thể handle? Giới hạn là gì? (file descriptors, memory)"

### NET-H02: Load balancer & Reverse proxy
**Câu hỏi:** Load balancer hoạt động thế nào? Phân biệt với reverse proxy. Có thể là bottleneck không?
**Keywords:** L4 (TCP) vs L7 (HTTP) LB, NAT, connection table, sticky session, health check
**Expected answer:**
- **L4 LB**: Forward packet dựa trên IP/port, không đọc HTTP content → nhanh
- **L7 LB**: Đọc HTTP headers, URL → route theo content (header-based routing)
- Response có thể bypass LB (Direct Server Return) hoặc qua LB
- **Bottleneck**: Network bandwidth (không phải CPU/RAM) → dùng anycast, multiple LB
**Follow-up:** "Reverse proxy khác LB thế nào? Nginx là gì — LB hay reverse proxy?"

### NET-H03: TCP keep-alive & connection lifetime
**Câu hỏi:** HTTP persistent connection là gì? Keep-alive hoạt động thế nào? Pros/cons?
**Keywords:** `Connection: keep-alive`, HTTP/1.1 default, pipelining, head-of-line blocking, timeout
**Expected answer:** HTTP/1.1 mặc định persistent — reuse TCP connection cho nhiều request. Giảm latency (không phải handshake lại). Nhưng head-of-line blocking: request sau phải chờ request trước xong.
**Follow-up:** "HTTP/2 multiplexing giải quyết HOL blocking thế nào?"
