# ⚙️ Functional Requirements Document (FRD)
## Beauty & Shine — POS-ERP Integration Engine V6

---

| Field | Value |
|---|---|
| **Project** | Beauty & Shine — Radiance & Refinement |
| **Document** | FRD v1.0 |
| **Author** | System Analyst |
| **Date** | 2026-05-27 |
| **Reference** | BRD v1.0, PRD v1.0, ERD v1.0 |
| **Status** | DRAFT — Pending Stakeholder Approval |

---

## 1. Document Purpose

FRD mendefinisikan fungsi-fungsi spesifik yang harus dimiliki sistem Beauty & Shine. Setiap requirement terikat dengan business rule dari BRD dan entity dari ERD.

---

## 2. Functional Module Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                  BEAUTY & SHINE SYSTEM MODULES                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │
│  │  AUTH   │  │   POS   │  │ BOOKING │  │ PAYMENT │          │
│  │ MODULE  │  │ MODULE  │  │ MODULE  │  │ MODULE  │          │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘          │
│                                                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │
│  │  STAFF  │  │PRODUCT/ │  │CUSTOMER │  │FINANCE  │          │
│  │ MODULE  │  │SERVICE  │  │& LOYALTY│  │ MODULE  │          │
│  └─────────┘  │ MODULE  │  │ MODULE  │  └─────────┘          │
│               └─────────┘  └─────────┘                         │
│                                                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                       │
│  │INVENTORY│  │DASHBOARD│  │  AUDIT  │                       │
│  │ MODULE  │  │& REPORTS│  │ MODULE  │                       │
│  └─────────┘  └─────────┘  └─────────┘                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Module 1: Authentication & Authorization (AUTH)

### 3.1 Functions

| ID | Function | Description | Priority |
|---|---|---|---|
| AUTH-F01 | User Login | Login dengan username + password, return JWT token | P0 |
| AUTH-F02 | Staff POS Login | Login dengan Staff ID + PIN, mulai shift | P0 |
| AUTH-F03 | JWT Token Generation | Generate access token (30 min) + refresh token (7 days) | P0 |
| AUTH-F04 | Role-Based Access | Middleware cek role sebelum akses endpoint | P0 |
| AUTH-F05 | Session Management | Track active session, force logout capability | P1 |
| AUTH-F06 | Password Hashing | bcrypt dengan min 12 rounds | P0 |
| AUTH-F07 | Audit Login/Logout | Record setiap login/logout ke audit_log | P1 |
| AUTH-F08 | Password Reset | Reset password via email verification | P2 |

### 3.2 Detailed Specifications

#### AUTH-F01: User Login
```
Input:    { username: string, password: string }
Process:  1. Validate input
          2. Find user by username
          3. Verify password (bcrypt compare)
          4. Generate JWT token
          5. Record login to audit_log
Output:   { success: true, token: string, role: string, redirect: string }
Error:    { success: false, message: "Invalid credentials" }
```

#### AUTH-F02: Staff POS Login
```
Input:    { staff_id: string, pin: string }
Process:  1. Validate input
          2. Find staff by staff_code
          3. Verify PIN (bcrypt compare)
          4. Create new SHIFT record (status: active)
          5. Return staff info + shift_id
Output:   { success: true, shift_id: string, staff: { id, name, role, branch } }
Error:    { success: false, message: "Staff not found / PIN incorrect" }
```

### 3.3 Business Rules
- BR-02: Kasir harus start shift sebelum bisa transaksi
- Password minimal 8 karakter, harus ada huruf + angka
- Session timeout: 30 menit idle
- Max 3 failed login attempts → lock 15 menit

---

## 4. Module 2: POS (Point of Sale)

### 4.1 Functions

| ID | Function | Description | Priority |
|---|---|---|---|
| POS-F01 | Start Shift | Kasir mulai shift dengan Staff ID + PIN | P0 |
| POS-F02 | End Shift | Tutup shift, generate Z-report | P0 |
| POS-F03 | Product Catalog | Tampilkan produk + layanan dengan harga | P0 |
| POS-F04 | Add to Cart | Tambah item ke keranjang | P0 |
| POS-F05 | Update Cart | Ubah quantity, hapus item | P0 |
| POS-F06 | Apply Discount | Diskon per-item atau per-transaksi | P1 |
| POS-F07 | Calculate Tax | Hitung PPN 11% dari subtotal | P0 |
| POS-F08 | Process Payment | Proses pembayaran (cash/VA/QRIS) | P0 |
| POS-F09 | Generate Receipt | Generate receipt data (HTML/PDF) | P0 |
| POS-F10 | Z-Report | Laporan penjualan harian per shift | P0 |
| POS-F11 | Customer Link | Link transaksi ke customer (opsional) | P1 |
| POS-F12 | Void Transaction | Batalkan transaksi (butuh approval manager) | P1 |
| POS-F13 | Print Receipt | Cetak receipt ke thermal printer | P0 |
| POS-F14 | Send Receipt via WhatsApp | Kirim receipt ke customer via WA | P1 |
| POS-F15 | Responsive Layout | UI adaptif untuk mobile, tablet, desktop | P0 |
| POS-F16 | PWA Install | Install POS sebagai app di Android/iPad | P0 |
| POS-F17 | Touch Optimization | Tap target 44px+, gesture support | P0 |
| POS-F18 | Portrait/Landscape | Support orientasi portrait dan landscape | P1 |

### 4.2 Detailed Specifications

#### POS-F04: Add to Cart
```
Input:    { product_id?: UUID, service_id?: UUID, quantity: integer }
Process:  1. Validate item exists and is active
          2. Check stock if product
          3. Add to cart array (client-side)
          4. Recalculate subtotal
Output:   { cart: [...items], subtotal: decimal, tax: decimal, total: decimal }
```

#### POS-F08: Process Payment
```
Input:    { shift_id: UUID, items: [...], customer_id?: UUID,
            discount?: decimal, payment_method: enum, amount_paid?: decimal }
Process:  1. Validate shift is active
          2. Calculate subtotal, discount, tax, total
          3. Generate invoice_number
          4. Create TRANSACTION record
          5. Create TRANSACTION_ITEM records
          6. Process payment (method-specific)
             - Cash: validate amount_paid >= total, calculate change
             - BCA VA: generate VA, set status pending
             - Midtrans: create Snap transaction
          7. Update stock (if product items)
          8. Generate journal entry (auto)
          9. Award loyalty points (if customer)
          10. Generate receipt
Output:   { success: true, invoice: string, total: decimal, change?: decimal,
            payment_url?: string (for VA/QRIS) }
```

#### POS-F09: Generate Receipt
```
Input:    { transaction_id: UUID }
Process:  1. Fetch transaction header (invoice, date, cashier, branch)
          2. Fetch transaction items (name, qty, price, subtotal)
          3. Calculate summary (subtotal, discount, tax, total, payment, change)
          4. Render receipt template:
             - Header: Beauty & Shine logo + branch name + address
             - Transaction: invoice number, date, cashier name
             - Items: name, qty × price = subtotal
             - Summary: subtotal, discount, PPN 11%, total
             - Payment: method, amount paid, change
             - Footer: "Terima kasih atas kunjungan Anda ✦"
          5. Generate PDF (for digital) or ESC/POS (for printer)
          6. Save to ATTACHMENT table
Output:   { receipt_html: string, receipt_pdf: path, receipt_escpos: bytes }
```

#### POS-F13: Print Receipt
```
Input:    { transaction_id: UUID, printer_id?: UUID }
Process:  1. Generate receipt (POS-F09)
          2. Detect connected printer (USB/Ethernet)
          3. Convert to ESC/POS format (58mm or 80mm paper)
          4. Send to printer
          5. Log print status
Output:   { success: true, printer: string, copies: 1 }
Fallback: If printer unavailable → show PDF download option

Printer Auto-Detect:
  - USB: /dev/usb/lp0 (ESC/POS compatible)
  - Network: TCP socket (192.168.x.x:9100)
  - Browser: window.print() fallback
```

#### POS-F14: Send Receipt via WhatsApp
```
Input:    { transaction_id: UUID, phone_number?: string }
Process:  1. Generate receipt PDF (POS-F09)
          2. Check customer phone (from transaction or manual input)
          3. Format WhatsApp message:
             ┌─────────────────────────────────┐
             │ 🧾 *Beauty & Shine*             │
             │ Receipt / Invoice               │
             │                                 │
             │ Invoice: INV-20260527-0001      │
             │ Date: 27 May 2026, 14:30        │
             │ Cashier: Siti                   │
             │                                 │
             │ 1x Facial Treatment  Rp 150.000 │
             │ 1x Body Massage     Rp 200.000 │
             │ ─────────────────────────────   │
             │ Subtotal            Rp 350.000  │
             │ PPN (11%)           Rp  38.500  │
             │ *Total*             *Rp 388.500*│
             │                                 │
             │ Terima kasih atas kunjungan ✦   │
             └─────────────────────────────────┘
          4. Send via WhatsApp Business API
          5. Attach PDF receipt (optional)
          6. Log notification status
Output:   { success: true, message_id: string, channel: "whatsapp" }
Fallback: If WA fails → offer download PDF or print

WhatsApp Business API:
  - Endpoint: POST /v1/messages
  - Template: receipt_template (pre-approved)
  - Media: PDF attachment via media_id
```

#### Receipt Template Design
```
┌──────────────────────────────────────┐
│         ✦ BEAUTY & SHINE ✦          │
│        Radiance & Refinement         │
│   Jl. Sudirman No. 123, Jakarta     │
│        Telp: 021-1234567            │
├──────────────────────────────────────┤
│ Invoice: INV-20260527-0001          │
│ Date:    27/05/2026 14:30           │
│ Cashier: Siti Nurhaliza             │
│ Branch:  HQ                         │
├──────────────────────────────────────┤
│ 1x Facial Treatment   Rp 150.000   │
│ 1x Body Massage       Rp 200.000   │
├──────────────────────────────────────┤
│ Subtotal              Rp 350.000   │
│ Discount              Rp     0     │
│ PPN 11%               Rp  38.500   │
│ ─────────────────────────────────── │
│ TOTAL                 Rp 388.500   │
├──────────────────────────────────────┤
│ Payment: Cash                        │
│ Paid:    Rp 400.000                 │
│ Change:  Rp  11.500                 │
├──────────────────────────────────────┤
│   Terima kasih atas kunjungan Anda  │
│         ✦ Beauty & Shine ✦          │
└──────────────────────────────────────┘
```

### 4.3 Business Rules
- BR-01: PPN 11% otomatis
- BR-02: Shift harus aktif untuk transaksi
- BR-03: Invoice format `INV-YYYYMMDD-XXXX`
- Cash: kembalian = amount_paid - total
- BCA VA: expired dalam 24 jam
- Void butuh approval manager (role check)

---

## 5. Module 3: Payment Integration

### 5.1 Functions

| ID | Function | Description | Priority |
|---|---|---|---|
| PAY-F01 | Generate BCA VA | Buat virtual account BCA untuk transaksi | P0 |
| PAY-F02 | Midtrans Snap | Buat transaksi Midtrans (QRIS, Card, Transfer) | P0 |
| PAY-F03 | Payment Callback | Handle webhook dari payment gateway | P0 |
| PAY-F04 | Check Status | Cek status pembayaran manual | P0 |
| PAY-F05 | Refund | Proses refund ke customer | P1 |
| PAY-F06 | Reconciliation | Match transaksi POS dengan settlement gateway | P1 |

### 5.2 Payment Flow per Method

```
┌─────────────┐
│  CASH       │
│  ─────────  │
│  amount_paid│──→ validate >= total
│  change     │──→ change = paid - total
│  status:paid│
└─────────────┘

┌─────────────┐
│  BCA VA     │
│  ─────────  │
│  generate VA│──→ POST /payments/bca-va
│  show VA no │──→ customer transfer
│  callback   │──→ webhook from BCA
│  status:paid│──→ update transaction
└─────────────┘

┌─────────────┐
│  MIDTRANS   │
│  ─────────  │
│  create Snap│──→ POST /payments/midtrans
│  redirect   │──→ customer pays via Snap
│  callback   │──→ webhook from Midtrans
│  status:paid│──→ update transaction
└─────────────┘
```

---

## 6. Module 4: Booking System

### 6.1 Functions

| ID | Function | Description | Priority |
|---|---|---|---|
| BK-F01 | Create Booking | Customer booking treatment | P0 |
| BK-F02 | Check Availability | Cek slot kosong berdasarkan staff & waktu | P0 |
| BK-F03 | Assign Staff | Auto/suggest staff berdasarkan availability | P0 |
| BK-F04 | Confirm Booking | Konfirmasi booking, kirim notifikasi | P0 |
| BK-F05 | Cancel Booking | Batalkan booking (rule: > 24 jam bebas penalti) | P0 |
| BK-F06 | Reschedule | Pindah jadwal booking | P1 |
| BK-F07 | No-Show Marking | Tandai customer no-show | P1 |
| BK-F08 | Booking Calendar View | Tampilan kalender untuk manager | P1 |

### 6.2 Detailed Specifications

#### BK-F01: Create Booking
```
Input:    { customer_id: UUID, service_id: UUID, preferred_staff_id?: UUID,
            booking_date: date, booking_time: time }
Process:  1. Validate service exists
          2. Check staff availability for date/time
          3. If preferred_staff unavailable, suggest alternatives
          4. Calculate end_time = booking_time + duration_minutes
          5. Generate booking_number
          6. Create BOOKING record (status: pending)
          7. Send confirmation notification
Output:   { success: true, booking_number: string, status: "confirmed" }
```

### 6.3 Business Rules
- BR-10: Cancel > 24 jam = no penalty, < 24 jam = catatan di customer profile
- Booking slot: 30 menit buffer antar booking
- Double booking prevention: UNIQUE constraint pada (staff_id, booking_date, booking_time)
- No-show 3x → flag customer

---

## 7. Module 5: Staff Management

### 7.1 Functions

| ID | Function | Description | Priority |
|---|---|---|---|
| STF-F01 | Create Staff | Tambah staff baru dengan role | P0 |
| STF-F02 | Update Staff | Edit data staff | P0 |
| STF-F03 | Deactivate Staff | Nonaktifkan staff (soft delete) | P0 |
| STF-F04 | PIN Management | Set/reset PIN staff | P0 |
| STF-F05 | Role Assignment | Assign role ke staff | P0 |
| STF-F06 | Shift Schedule | Buat dan manage jadwal shift | P1 |
| STF-F07 | Commission Tracking | Hitung komisi berdasarkan service | P1 |
| STF-F08 | Attendance Log | Record kehadiran staff | P1 |
| STF-F09 | Performance Report | Laporan performa staff | P2 |

### 7.2 Staff Role Matrix

| Permission | Super Admin | Owner | Manager | Kasir | Therapist |
|---|---|---|---|---|---|
| System config | ✅ | ❌ | ❌ | ❌ | ❌ |
| User management | ✅ | ✅ | ❌ | ❌ | ❌ |
| Financial reports | ✅ | ✅ | ✅ | ❌ | ❌ |
| Staff management | ✅ | ✅ | ✅ | ❌ | ❌ |
| POS transactions | ✅ | ✅ | ✅ | ✅ | ❌ |
| Shift management | ✅ | ✅ | ✅ | ✅ | ❌ |
| Inventory | ✅ | ✅ | ✅ | ❌ | ❌ |
| Booking management | ✅ | ✅ | ✅ | ✅ | ❌ |
| Own schedule | ✅ | ✅ | ✅ | ✅ | ✅ |
| Treatment log | ✅ | ❌ | ✅ | ❌ | ✅ |

---

## 8. Module 6: Product & Service Management

### 8.1 Functions

| ID | Function | Description | Priority |
|---|---|---|---|
| PS-F01 | Create Product | Tambah produk baru | P0 |
| PS-F02 | Update Product | Edit produk | P0 |
| PS-F03 | Delete Product | Hapus/nonaktifkan produk | P0 |
| PS-F04 | Create Service | Tambah layanan baru | P0 |
| PS-F05 | Update Service | Edit layanan | P0 |
| PS-F06 | Category Management | Manage kategori produk/service | P1 |
| PS-F07 | Price History | Track perubahan harga | P2 |
| PS-F08 | Bulk Import | Import produk dari CSV/Excel | P2 |

---

## 9. Module 7: Customer & Loyalty

### 9.1 Functions

| ID | Function | Description | Priority |
|---|---|---|---|
| CUS-F01 | Register Customer | Daftar customer baru | P0 |
| CUS-F02 | Update Profile | Edit data customer | P0 |
| CUS-F03 | Search Customer | Cari by name/phone/code | P0 |
| CUS-F04 | Visit History | Lihat riwayat kunjungan | P1 |
| CUS-F05 | Earn Points | Tambah poin dari transaksi | P1 |
| CUS-F06 | Redeem Points | Tukar poin jadi diskon | P1 |
| CUS-F07 | Tier Upgrade | Auto upgrade tier berdasarkan spending | P1 |
| CUS-F08 | Birthday Reward | Auto reward di bulan ulang tahun | P2 |
| CUS-F09 | Referral Program | Reward untuk referral | P2 |

### 9.2 Loyalty Tier Rules

| Tier | Min Spending | Benefit |
|---|---|---|
| Bronze | Rp 0 | Base earn rate (1 pt / Rp 10.000) |
| Silver | Rp 2.000.000 | 1.2x earn rate, priority booking |
| Gold | Rp 5.000.000 | 1.5x earn rate, birthday gift, free upgrade |
| Platinum | Rp 15.000.000 | 2x earn rate, exclusive events, personal consultant |

---

## 10. Module 8: Inventory Management

### 10.1 Functions

| ID | Function | Description | Priority |
|---|---|---|---|
| INV-F01 | Stock View | Lihat stok saat ini per produk per cabang | P0 |
| INV-F02 | Stock Adjustment | Koreksi stok (opname) | P0 |
| INV-F03 | Stock Movement Log | Track semua pergerakan stok | P0 |
| INV-F04 | Low Stock Alert | Notifikasi jika stok ≤ minimum | P1 |
| INV-F05 | Stock Transfer | Transfer stok antar cabang | P2 |
| INV-F06 | Purchase Order | Buat PO ke supplier | P2 |

### 10.2 Stock Movement Types

| Type | Description | Effect on Stock |
|---|---|---|
| IN | Stok masuk (pembelian/penerimaan) | +qty |
| OUT | Stok keluar (penjualan POS) | -qty |
| ADJUSTMENT | Koreksi (opname) | ±qty |
| TRANSFER_IN | Terima transfer dari cabang lain | +qty |
| TRANSFER_OUT | Kirim transfer ke cabang lain | -qty |

---

## 11. Module 9: Finance & Accounting

### 11.1 Functions

| ID | Function | Description | Priority |
|---|---|---|---|
| FIN-F01 | Auto Journal Entry | Generate jurnal otomatis dari transaksi | P0 |
| FIN-F02 | COA Management | Manage chart of accounts | P0 |
| FIN-F03 | Revenue Report | Laporan pendapatan (daily/weekly/monthly) | P0 |
| FIN-F04 | Expense Tracking | Input dan track pengeluaran | P1 |
| FIN-F05 | P&L Statement | Laba rugi otomatis | P1 |
| FIN-F06 | Period Lock | Lock periode akuntansi | P1 |
| FIN-F07 | Tax Report | Laporan PPN | P1 |
| FIN-F08 | Cash Flow | Arus kas | P2 |

### 11.2 Auto Journal Entry Rules

**POS Transaction (Cash Payment):**
```
Debit:  Kas di Tangan (1001)     Rp 111.000
Credit: Pendapatan Jasa (4000)   Rp 100.000
Credit: Utang Pajak PPN (2100)   Rp  11.000
```

**POS Transaction (BCA VA Payment):**
```
Debit:  Bank BCA (1002)          Rp 111.000
Credit: Pendapatan Jasa (4000)   Rp 100.000
Credit: Utang Pajak PPN (2100)   Rp  11.000
```

---

## 12. Module 10: Dashboard & Reports

### 12.1 Functions

| ID | Function | Description | Priority |
|---|---|---|---|
| RPT-F01 | Owner Dashboard | Revenue, transaksi, staff summary | P0 |
| RPT-F02 | Real-time Monitor | Transaksi berlangsung real-time | P0 |
| RPT-F03 | Sales by Service | Penjualan per layanan | P0 |
| RPT-F04 | Sales by Staff | Penjualan per staff | P1 |
| RPT-F05 | Sales by Period | Harian/mingguan/bulanan | P0 |
| RPT-F06 | Customer Analytics | Top customer, visit frequency | P1 |
| RPT-F07 | Inventory Report | Stock level, movement | P1 |
| RPT-F08 | Export | Export ke Excel/PDF | P1 |

---

## 13. Module 11: Audit & System

### 13.1 Functions

| ID | Function | Description | Priority |
|---|---|---|---|
| AUD-F01 | Audit Logging | Record semua perubahan data | P0 |
| AUD-F02 | System Health | Monitor CPU, RAM, disk | P1 |
| AUD-F03 | Backup | Daily automated backup | P0 |
| AUD-F04 | Error Logging | Structured error logging | P0 |

---

## 14. Functional Traceability Matrix

| FRD ID | Module | BRD Ref | ERD Entity | Priority |
|---|---|---|---|---|
| AUTH-F01 | Auth | BR-M01 | STAFF | P0 |
| AUTH-F02 | Auth | BR-02 | STAFF, SHIFT | P0 |
| POS-F01 | POS | BR-02 | SHIFT | P0 |
| POS-F08 | POS | BR-M01 | TRANSACTION, PAYMENT | P0 |
| PAY-F01 | Payment | BR-M02 | PAYMENT | P0 |
| PAY-F02 | Payment | BR-M02 | PAYMENT | P0 |
| BK-F01 | Booking | BR-S01 | BOOKING | P0 |
| CUS-F01 | Customer | BR-M06 | CUSTOMER | P0 |
| CUS-F05 | Loyalty | BR-S02 | LOYALTY_TRANSACTION | P1 |
| FIN-F01 | Finance | BR-M07 | JOURNAL_ENTRY, JOURNAL_LINE | P0 |
| RPT-F01 | Dashboard | BR-M03, SO-4 | (aggregated) | P0 |

---

## 15. UI Wireframe Summary

| Page | Elements | Interaction |
|---|---|---|
| Landing Page | Hero, Services, Testimonials, CTA | Scroll animations, "Begin Your Glow" CTA |
| Login Page | Username, Password, Sign In button | Form submit → redirect by role |
| POS Terminal | Product grid, Cart, Payment button | Click product → cart → checkout |
| Dashboard | KPI cards, Charts, Activity table | Real-time data, date filter |
| Booking Page | Calendar, Service selector, Staff selector | Date/time pick, confirm |

---

## 16. API Functional Mapping

| API Endpoint | FRD Function | Method |
|---|---|---|
| POST /auth/login | AUTH-F01 | POST |
| POST /pos/auth | AUTH-F02 | POST |
| POST /pos/transactions | POS-F08 | POST |
| GET /pos/z-report | POS-F10 | GET |
| POST /payments/bca-va | PAY-F01 | POST |
| POST /payments/midtrans | PAY-F02 | POST |
| POST /payments/callback | PAY-F03 | POST |
| POST /bookings | BK-F01 | POST |
| GET /bookings/availability | BK-F02 | GET |
| POST /customers | CUS-F01 | POST |
| GET /customers/:id/history | CUS-F04 | GET |
| GET /products | PS-F01 | GET |
| GET /inventory | INV-F01 | GET |
| POST /inventory/adjust | INV-F02 | POST |
| GET /reports/revenue | RPT-F05 | GET |

---

*Document ini harus di-review dan di-approve oleh stakeholder sebelum development phase dimulai.*
