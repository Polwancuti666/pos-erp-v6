# Security Policy

## Melaporkan Vulnerability

Kami sangat menghargai laporan vulnerability dari komunitas. Jika Anda menemukan masalah keamanan, **jangan buka public issue**.

### Cara Melapor

Kirim email ke: **[security@beautynshine.web.id]** *(atau hubungi maintainer secara langsung)*

Sertakan informasi berikut:

- **Deskripsi** vulnerability yang ditemukan
- **Langkah reproduksi** (step-by-step)
- **Dampak potensial** yang mungkin terjadi
- **Saran perbaikan** (jika ada)

### Response Timeline

| Tahap | Target Waktu |
|---|---|
| Acknowledgement | 24 jam |
| Initial assessment | 72 jam |
| Fix development | 7 hari (tergantung severity) |
| Release patch | 14 hari (tergantung severity) |

Kami akan berkomunikasi dengan Anda selama proses ini dan memberikan credit (jika diinginkan) setelah vulnerability diperbaiki.

---

## Security Measures yang Diterapkan

### Autentikasi & Otorisasi

- **RBAC (Role-Based Access Control):** 5 roles (cashier, branch_manager, accounting_lead, it_admin, owner) dengan 11 granular actions
- **Staff PIN Auth:** Autentikasi kasir dengan PIN + shift management
- **ERP Login:** Separate credential system untuk admin/kasir
- **Session Management:** Shift-based session dengan automatic timeout

### Enkripsi & Keamanan Data

- **EncryptionService:** XOR + HMAC untuk data sensitif
- **SecretPolicy:** Kebijakan rotasi dan management secret keys
- **HMAC Signature Verification:** Untuk semua payment webhook callbacks (BCA VA, Midtrans)
- **Staff Reservation Locks:** Timeout 10 menit dengan audit logging

### Payment Security

- **Webhook Signature Verification:** Semua incoming webhook diverifikasi via HMAC
- **Payment Verification Flow:** Multi-step verification (QRIS callback, bank transfer, manual proof)
- **No Plaintext Credentials:** Secret keys tidak disimpan dalam plaintext di kode

### Infrastructure

- **PostgreSQL 16:** Database dengan parameterized queries (no SQL injection)
- **Cloudflare Tunnel:** Akses ke service melalui tunnel, bukan direct exposure
- **Docker Isolation:** Service berjalan dalam container terisolasi

### Observability & Monitoring

- **Health Checks:** Endpoint `/health` memeriksa database, outbox, ERP, dan payment
- **MetricsRegistry:** Monitoring performa dan error rates
- **Exception Queue:** SLA tracking (2h–24h) untuk semua exception
- **Audit Logging:** Semua aksi kritis dicatat (staff locks, corrections, sync)

### Data Integrity

- **Period Lock:** Prevent modifikasi data pada periode akuntansi yang sudah ditutup
- **Document Numbering:** Penomoran dokumen yang terurut dan tidak bisa diubah
- **Sync Outbox Pattern:** Memastikan data tidak hilang saat offline
- **Correction Matrix:** Koreksi transaksi hanya melalui workflow yang terstruktur

---

## Best Practices untuk Kontributor

1. **Jangan commit secrets** — gunakan `.env` dan `.env.example`
2. **Jangan hardcode credentials** — selalu gunakan environment variables
3. **Validasi semua input** — terutama untuk payment dan external API
4. **Verifikasi signatures** — semua webhook harus diverifikasi HMAC
5. **Gunakan parameterized queries** — hindari string concatenation untuk SQL
6. **Update dependencies** — periksa CVE secara berkala
7. **Test security paths** — pastikan auth dan permission checks tercover di test

---

## Dependencies Security

```bash
# Cek vulnerability di dependencies
pip audit

# Update dependencies
pip install --upgrade -r requirements.txt
```

Lakukan security audit dependencies secara berkala, terutama sebelum release.

---

## Disclosure Policy

- Kami mengikuti responsible disclosure
- Vulnerability akan di-fix sebelum public disclosure
- Contributor akan dikreditkan (kecuali ingin anonymous)
- Kami tidak mengambil tindakan legal terhadap researcher yang melapor secara bertanggung jawab
