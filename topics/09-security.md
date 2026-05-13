# Security — Question Bank

> Nguồn: cs_questions.txt — SECURITY section

---

## EASY

### SEC-E01: Hash vs Encrypt vs Encode
**Câu hỏi:** Phân biệt Hashing, Encryption, và Encoding. Khi nào dùng cái nào?
**Keywords:** one-way, reversible, lossless, Base64, SHA256, AES, bcrypt
**Expected answer:**
| | Hashing | Encryption | Encoding |
|--|---------|-----------|---------|
| Reversible? | ❌ one-way | ✅ với key | ✅ lossless |
| Purpose | Integrity, password | Confidentiality | Data format (transport) |
| Example | SHA256, bcrypt | AES, RSA | Base64, URL encoding |
| Key needed? | ❌ | ✅ | ❌ |

- **Hash passwords**: bcrypt/argon2 (slow hash) — KHÔNG SHA256 (fast hash, GPU-crackable)
- **Encrypt**: API keys, sensitive config
- **Encode**: Transmit binary data as text (Base64 in JWT payload)
**Follow-up:** "Tại sao dùng slow hash (bcrypt) cho password thay vì SHA256?"

### SEC-E02: Symmetric vs Asymmetric Encryption
**Câu hỏi:** Phân biệt symmetric và asymmetric encryption. AES vs RSA. Khi nào dùng cái nào?
**Keywords:** shared key, public/private key pair, performance, key exchange problem, hybrid encryption
**Expected answer:**
- **Symmetric (AES)**: Cùng key để encrypt/decrypt. Nhanh. Vấn đề: key distribution.
- **Asymmetric (RSA)**: Public key encrypt, private key decrypt (hoặc ngược lại cho signing). Chậm hơn.
- **Thực tế**: Dùng asymmetric để trao đổi symmetric key an toàn (TLS handshake), sau đó dùng symmetric để transfer data.
**Follow-up:** "JWT signing dùng symmetric (HS256) hay asymmetric (RS256)? Khi nào dùng cái nào?"

### SEC-E03: Fast Hash vs Slow Hash
**Câu hỏi:** Tại sao password phải dùng slow hash (bcrypt, argon2) thay vì MD5/SHA256?
**Keywords:** GPU brute-force, rainbow table, salt, work factor, cost parameter
**Expected answer:** MD5/SHA256 được thiết kế để nhanh → GPU có thể thử hàng tỉ hashes/second → dictionary attack, rainbow table attack. bcrypt/argon2 có work factor (cost) — chậm có chủ ý. Salt ngăn rainbow table.
**Follow-up:** "Salt là gì? bcrypt có tự gen salt không? Tại sao không nên dùng cùng 1 salt cho tất cả users?"

---

## MEDIUM

### SEC-M01: SSL/TLS deep dive
**Câu hỏi:** Certificate là gì? CA là gì? Làm sao browser verify certificate?
**Keywords:** X.509, CA chain, self-signed, digital signature, certificate pinning, OCSP
**Expected answer:**
1. Certificate chứa: public key, domain, issuer (CA), expiry, digital signature của CA
2. Browser verify: Check CA signature (dùng CA's public key trong browser trust store) → check domain → check expiry
3. **CA chain**: Leaf cert ← Intermediate CA ← Root CA (trusted by OS/browser)
4. **Self-signed**: Không có CA verify → browser warning
**Follow-up:** "Nếu CA bị compromise, điều gì xảy ra? Certificate Revocation (CRL/OCSP) là gì?"

### SEC-M02: Digital Signature & HMAC
**Câu hỏi:** Digital signature là gì? Phân biệt với HMAC. JWT signing dùng cái nào?
**Keywords:** sign with private key, verify with public key, non-repudiation, HMAC shared secret
**Expected answer:**
- **Digital signature**: Sign bằng private key, verify bằng public key → non-repudiation (chứng minh ai sign)
- **HMAC**: Hash + shared secret → verify integrity + authenticity, nhưng cả 2 bên đều có secret → không có non-repudiation
- **JWT HS256**: HMAC-SHA256 (symmetric, shared secret) → chỉ dùng khi 1 service cả sign lẫn verify
- **JWT RS256**: RSA signature → service A sign, service B verify với public key — tốt cho microservices
**Follow-up:** "JWT payload có được encrypt không? Nếu không, bạn có lưu sensitive data vào payload không?"

### SEC-M03: Store Credentials Securely
**Câu hỏi:** Làm thế nào store password, API keys, database credentials, secret keys một cách an toàn?
**Keywords:** bcrypt/argon2, environment variables, secrets manager (AWS Secrets Manager, Vault), `.env`, never in code/git
**Expected answer:**
- **User passwords**: bcrypt/argon2 với salt, KHÔNG plain text hoặc symmetric encrypt
- **API keys / DB credentials**: Environment variables, KHÔNG hardcode trong source code
- **Production**: AWS Secrets Manager, HashiCorp Vault — rotation tự động, audit log
- **Config**: `.env` file không commit vào git (`.gitignore`), dùng `.env.example` làm template
**CV link:** "Bạn deploy lên AWS ECS ở Atrix AI — secrets inject vào container thế nào? (ECS Task Definition environment variables / Secrets Manager ARN)"

### SEC-M04: Cookie security & Session hijacking
**Câu hỏi:** Cookie bị đánh cắp thì attacker có thể login được không? Làm thế nào mitigate?
**Keywords:** HttpOnly, Secure flag, SameSite, XSS, CSRF, session fixation
**Expected answer:**
- **HttpOnly**: JavaScript không đọc được cookie → ngăn XSS steal cookie
- **Secure**: Chỉ gửi qua HTTPS
- **SameSite=Strict/Lax**: Ngăn CSRF (cross-site request forgery)
- **Session rotation**: Sau login, tạo session ID mới → ngăn session fixation
- **Short expiry + refresh token**: Access token ngắn hạn (15 phút), refresh token dài hạn
**Follow-up:** "XSS và CSRF khác nhau thế nào? Cách defend từng loại?"

---

## HARD

### SEC-H01: JWT deep dive
**Câu hỏi:** JWT structure là gì? Token revocation vấn đề thế nào? Cách giải quyết?
**Keywords:** header.payload.signature, stateless, revocation list, blacklist, short-lived + refresh
**Expected answer:**
```
JWT = base64(header) + "." + base64(payload) + "." + signature
```
**Revocation problem**: JWT stateless → server không track. Nếu user logout, token vẫn valid đến expiry.
**Solutions**:
1. Short-lived access token (15 min) + long-lived refresh token (stored in DB → can revoke)
2. Token blacklist trong Redis (check mỗi request)
3. Token versioning: User có `token_version` field, JWT chứa version → compare khi verify
**CV link:** "Bạn implement OAuth2 + JWT + Casbin ở DG External. Refresh token flow như thế nào?"

### SEC-H02: DDoS Defense
**Câu hỏi:** DDoS là gì? Các loại DDoS khác nhau? Cách defend?
**Keywords:** volumetric (network), protocol (SYN flood), application layer (HTTP flood), rate limiting, CDN, WAF
**Expected answer:**
- **Volumetric**: Flood bandwidth → CDN absorb (Cloudflare)
- **SYN flood**: Fill connection table → SYN cookies, rate limit
- **HTTP flood (L7)**: Hợp lệ HTTP requests nhưng nhiều → rate limiting, CAPTCHA, WAF rules, bot detection
**Defense layers**:
1. CDN / anycast (absorb volumetric)
2. Rate limiting (per IP, per user)
3. WAF (Web Application Firewall)
4. Auto-scaling (absorb spike)
5. Monitoring + alert
**Follow-up:** "Rate limiting ở đâu là tốt nhất — application code hay infra layer? Trade-off?"

### SEC-H03: Hash cracking & Rainbow table
**Câu hỏi:** Có thể crack hash không? Rainbow table là gì? Salt giải quyết thế nào?
**Keywords:** precomputed table, salt uniqueness, time-space tradeoff, GPU hashrate, collision
**Expected answer:**
- **Brute force**: Thử tất cả combinations → quá chậm với dài
- **Dictionary attack**: Wordlist phổ biến → MD5("password") matches
- **Rainbow table**: Precomputed hash→plaintext table → O(1) lookup. Trade: storage
- **Salt**: Random string thêm vào password trước khi hash → mỗi user có hash khác nhau → rainbow table vô dụng (phải build table riêng cho từng salt)
```python
import bcrypt
# bcrypt tự gen salt và nhúng vào hash
hashed = bcrypt.hashpw(b"password123", bcrypt.gensalt(rounds=12))
# $2b$12$<22-char-salt><31-char-hash>
```
