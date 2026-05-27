# 📊 Business Requirements Document (BRD)
## Beauty & Shine — POS-ERP Integration Engine V6

---

| Field | Value |
|---|---|
| **Project** | Beauty & Shine — Radiance & Refinement |
| **Document** | BRD v1.0 |
| **Author** | System Analyst |
| **Date** | 2026-05-27 |
| **Status** | DRAFT — Pending Stakeholder Approval |
| **Classification** | Internal — Confidential |

---

## 1. Document Purpose

Dokumen ini mendefinisikan kebutuhan bisnis dari platform Beauty & Shine. BRD menjadi acuan utama bagi seluruh stakeholder (Owner, Manager, Development Team) untuk memastikan sistem yang dibangun sesuai dengan tujuan bisnis.

**Scope:** POS (Point of Sale) dan ERP (Enterprise Resource Planning) untuk industri beauty & wellness.

---

## 2. Business Background

### 2.1 Company Profile
- **Nama:** Beauty & Shine
- **Industri:** Beauty & Wellness Services
- **Layanan:** Facial, Hair Care, Nail Art, Body Treatment, Lash & Brow
- **Target Market:** Perempuan usia 20-45, kelas menengah-atas
- **Lokasi:** Jakarta (ekspansi ke kota lain direncanakan)

### 2.2 Current State (As-Is)
| Proses | Metode Saat Ini | Masalah |
|---|---|---|
| Transaksi penjualan | Manual (bon kertas) | Tidak tercatat rapi, rawan hilang |
| Pembayaran | Cash only | Tidak ada opsi cashless |
| Inventory | Excel spreadsheet | Stok tidak real-time, sering selisih |
| Laporan keuangan | Manual hitung | Lambat, rentan human error |
| Jadwal staff | WhatsApp group | Tidak terstruktur, sering miss komunikasi |
| Customer data | Tidak ada database | Tidak bisa follow-up, tidak ada loyalty |
| Booking | Telepon/WA langsung | Sering double booking, tidak ada reminder |

### 2.3 Future State (To-Be)
| Proses | Solusi Digital | Benefit |
|---|---|---|
| Transaksi penjualan | POS system digital | Real-time, tercatat otomatis |
| Pembayaran | Cash + BCA VA + Midtrans (QRIS/Card) | Multiple payment options |
| Inventory | Real-time stock tracking | Akurasi 99.5%, alert low stock |
| Laporan keuangan | Auto-generated reports | Instant, accurate, exportable |
| Jadwal staff | Digital scheduling | Terstruktur, ada notifikasi |
| Customer data | CRM database | Profiling, loyalty, follow-up |
| Booking | Online booking system | No double booking, auto-reminder |

---

## 3. Business Objectives

### 3.1 Strategic Objectives

| # | Objective | Success Metric | Target | Timeline |
|---|---|---|---|---|
| SO-1 | Digitalisasi operasional toko | % proses terdigitalisasi | 90%+ | 8 minggu |
| SO-2 | Meningkatkan revenue melalui payment modernization | Transaksi cashless | 40%+ dari total | 12 minggu |
| SO-3 | Customer retention melalui loyalty program | Repeat customer rate | 40%+ | 16 minggu |
| SO-4 | Data-driven decision making | Laporan otomatis tersedia | 100% | 8 minggu |
| SO-5 | Scalability untuk multi-branch | Cabang baru onboarding time | < 3 hari | 24 minggu |

### 3.2 Business Rules

| # | Rule | Description |
|---|---|---|
| BR-01 | PPN 11% | Semua transaksi dikenakan pajak 11% |
| BR-02 | Shift wajib | Kasir harus start shift sebelum bisa transaksi |
| BR-03 | Invoice numbering | Format: `INV-YYYYMMDD-XXXX` (auto-increment) |
| BR-04 | Payment confirmation | Transaksi dianggap "paid" setelah payment confirmed |
| BR-05 | Period lock | Bulan yang sudah di-close tidak bisa di-edit |
| BR-06 | Loyalty earn rate | 1 poin per Rp 10.000 belanja |
| BR-07 | Loyalty redeem rate | 100 poin = Rp 10.000 diskon |
| BR-08 | Staff commission | Diambil dari harga service, bukan produk |
| BR-09 | Stock minimum alert | Alert jika stok ≤ min_stock |
| BR-10 | Booking cancellation | Bisa cancel tanpa penalti jika > 24 jam sebelum jadwal |

---

## 4. Stakeholder Analysis

### 4.1 Stakeholder Map

```
                    HIGH INFLUENCE
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         │   Keep        │   Manage      │
         │   Satisfied   │   Closely     │
         │               │               │
         │   - Manager   │   - Owner     │
HIGH ────┼───────────────┼───────────────┼──── LOW
INTEREST │               │               │   INTEREST
         │   Monitor     │   Keep        │
         │   (Light)     │   Informed    │
         │               │               │
         │   - Vendor    │   - Kasir     │
         │   - Accountant│   - Customer  │
         │               │   - Therapist │
         └───────────────┼───────────────┘
                         │
                    LOW INFLUENCE
```

### 4.2 Stakeholder Detail

| Stakeholder | Role | Interest | Influence | Requirements |
|---|---|---|---|---|
| **Owner** | Decision maker | Strategic | High | Dashboard, reports, financial control |
| **Manager** | Operations | Tactical | Medium | Staff management, inventory, daily ops |
| **Kasir** | Front-line | Operational | Low | Easy POS, fast checkout, shift mgmt |
| **Therapist/Staff** | Service delivery | Operational | Low | Schedule view, commission tracking |
| **Customer** | Revenue source | Experience | Low | Booking, loyalty, seamless payment |
| **Accountant** | Finance | Compliance | Low | Journal entries, tax reporting, reconciliation |
| **IT Support** | Technical | Maintenance | Low | System monitoring, troubleshooting |

---

## 5. Business Processes

### 5.1 Core Business Process Map

```
┌─────────────────────────────────────────────────────────────────┐
│                    BEAUTY & SHINE PROCESS MAP                   │
└─────────────────────────────────────────────────────────────────┘

CUSTOMER JOURNEY                    BACK OFFICE
═══════════════                     ═══════════

┌──────────┐                        ┌──────────┐
│ DISCOVER │──→ Landing Page        │ MARKETING│
│          │    Social Media        │          │
└────┬─────┘                        └──────────┘
     │
     ▼
┌──────────┐                        ┌──────────┐
│  BOOK    │──→ Online/Walk-in      │ SCHEDULE │──→ Staff Assignment
│          │                        │  MGMT    │    Room Allocation
└────┬─────┘                        └──────────┘
     │
     ▼
┌──────────┐                        ┌──────────┐
│  CHECK   │──→ Arrival confirmation│ RECEPTION│──→ Queue Management
│   IN     │                        │          │
└────┬─────┘                        └──────────┘
     │
     ▼
┌──────────┐                        ┌──────────┐
│ TREATMENT│──→ Service delivery    │  STAFF   │──→ Treatment Log
│          │                        │  OPS     │    Quality Check
└────┬─────┘                        └──────────┘
     │
     ▼
┌──────────┐                        ┌──────────┐
│  CHECKOUT│──→ POS transaction     │  FINANCE │──→ Journal Entry
│  & PAY   │    Payment processing  │          │    Revenue Record
└────┬─────┘                        └──────────┘
     │
     ▼
┌──────────┐                        ┌──────────┐
│ FOLLOW   │──→ Loyalty points      │   CRM    │──→ Customer Profiling
│   UP     │    Review request      │          │    Campaign
└──────────┘                        └──────────┘
```

### 5.2 Key Process Descriptions

#### BPMN: POS Transaction Process
```
┌─────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Start   │────→│ Staff Login │────→│ Select Items │────→│ Apply       │
│  Shift   │     │ (ID + PIN)  │     │ (Cart Build) │     │ Discount?   │
└─────────┘     └─────────────┘     └──────────────┘     └──────┬──────┘
                                                                │
                          ┌─────────────────────────────────────┘
                          ▼
                   ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
                   │ Calculate    │────→│ Select       │────→│ Process     │
                   │ Tax (PPN)   │     │ Payment      │     │ Payment     │
                   └──────────────┘     └──────────────┘     └──────┬──────┘
                                                                    │
                          ┌─────────────────────────────────────────┘
                          ▼
                   ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
                   │ Payment      │────→│ Generate     │────→│ Update      │
                   │ Confirmed?   │     │ Receipt      │     │ Inventory   │
                   └──────┬───────┘     └──────────────┘     └──────┬──────┘
                          │                                         │
                          │ NO                                      ▼
                          │                                  ┌─────────────┐
                          ▼                                  │ Auto Journal│
                   ┌──────────────┐                          │ Entry       │
                   │ Retry /      │                          └──────┬──────┘
                   │ Alt Payment  │                                 │
                   └──────────────┘                                 ▼
                                                            ┌─────────────┐
                                                            │ Loyalty     │
                                                            │ Points      │
                                                            └──────┬──────┘
                                                                   │
                                                                   ▼
                                                            ┌─────────────┐
                                                            │    END      │
                                                            └─────────────┘
```

#### BPMN: Booking Process
```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│ Customer │────→│ Select       │────→│ Select       │────→│ Check       │
│ Initiates│     │ Service      │     │ Date/Time    │     │ Availability│
└──────────┘     └──────────────┘     └──────────────┘     └──────┬──────┘
                                                                  │
                          ┌───────────────────────────────────────┘
                          ▼
                   ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
                   │ Available?   │────→│ Assign       │────→│ Confirm     │
                   │              │ YES │ Staff        │     │ Booking     │
                   └──────┬───────┘     └──────────────┘     └──────┬──────┘
                          │ NO                                       │
                          ▼                                          ▼
                   ┌──────────────┐                          ┌─────────────┐
                   │ Suggest      │                          │ Send        │
                   │ Alternative  │                          │ Notification│
                   └──────────────┘                          └─────────────┘
```

---

## 6. Business Requirements Matrix

### 6.1 Must Have (MoSCoW - Must)

| # | Requirement | Business Justification | Owner |
|---|---|---|---|
| BR-M01 | Digital POS transaksi | Hapus transaksi manual, kurangi human error | Owner |
| BR-M02 | Multiple payment methods | Jangkau customer cashless, tingkatkan conversion | Owner |
| BR-M03 | Real-time revenue dashboard | Owner bisa monitor bisnis kapan saja | Owner |
| BR-M04 | Staff shift management | Kontrol kasir, cegah fraud | Manager |
| BR-M05 | Service catalog management | Konsistensi harga di semua cabang | Manager |
| BR-M06 | Customer database | Profiling untuk marketing & retention | Owner |
| BR-M07 | Automated financial reports | Kurangi waktu manual reporting | Owner |
| BR-M08 | Inventory tracking | Cegah stok hilang, optimasi purchasing | Manager |

### 6.2 Should Have (MoSCoW - Should)

| # | Requirement | Business Justification | Owner |
|---|---|---|---|
| BR-S01 | Online booking system | Customer convenience, kurangi double booking | Owner |
| BR-S02 | Loyalty points program | Retention, repeat purchase | Owner |
| BR-S03 | Staff commission tracking | Motivasi staff, transparansi | Manager |
| BR-S04 | Receipt printing (thermal) | Professional image, customer record | Manager |
| BR-S05 | Discount/promo management | Marketing flexibility | Owner |

### 6.3 Could Have (MoSCoW - Could)

| # | Requirement | Business Justification | Owner |
|---|---|---|---|
| BR-C01 | Multi-branch consolidation | Ekspansi bisnis | Owner |
| BR-C02 | Customer WhatsApp notification | Engagement, reminder | Owner |
| BR-C03 | Staff scheduling calendar | Optimasi jadwal | Manager |
| BR-C04 | Referral program | Organic growth | Owner |

### 6.4 Won't Have (This Phase)

| # | Requirement | Reason |
|---|---|---|
| BR-W01 | Mobile app (native) | Phase 2, web-first approach |
| BR-W02 | Franchise management | Too complex for MVP |
| BR-W03 | AI recommendation engine | Nice to have, not critical |

---

## 7. Financial Impact Analysis

### 7.1 Cost of Current State (Manual)
| Item | Monthly Cost | Annual Cost |
|---|---|---|
| Human error (stok selisih) | Rp 2.000.000 | Rp 24.000.000 |
| Lost transactions (bon hilang) | Rp 1.500.000 | Rp 18.000.000 |
| Staff overtime (manual report) | Rp 3.000.000 | Rp 36.000.000 |
| Customer loss (no loyalty/follow-up) | Rp 5.000.000 | Rp 60.000.000 |
| **Total Loss** | **Rp 11.500.000** | **Rp 138.000.000** |

### 7.2 Investment (Digital System)
| Item | One-time Cost | Monthly Cost |
|---|---|---|
| Development (8 weeks) | Rp 50.000.000 | - |
| VPS hosting (2 vCPU/4GB) | - | Rp 500.000 |
| Domain + SSL | Rp 500.000 | - |
| Payment gateway fee | - | 1.5-3% per txn |
| Maintenance & support | - | Rp 2.000.000 |
| **Total** | **Rp 50.500.000** | **Rp 2.500.000 + % txn** |

### 7.3 Expected ROI
| Metric | Value |
|---|---|
| Annual savings (reduced loss) | Rp 138.000.000 |
| Annual investment | Rp 80.500.000 (one-time + 12 months) |
| **Net benefit Year 1** | **Rp 57.500.000** |
| **ROI** | **71.4%** |
| **Payback period** | **~7 bulan** |

---

## 8. Risk Assessment

| # | Risk | Impact | Probability | Mitigation | Owner |
|---|---|---|---|---|---|
| R-01 | Staff resistensi terhadap perubahan | High | Medium | Training, gradual rollout | Manager |
| R-02 | Internet down saat peak hours | High | Low | Offline mode, backup internet | IT |
| R-03 | Payment gateway delay/blocked | Medium | Medium | Multiple gateway, manual fallback | Owner |
| R-04 | Data migration error | Medium | Low | Validation, backup before migration | IT |
| R-05 | Scope creep | Medium | High | Strict MoSCoW, change control | Owner |
| R-06 | VPS resource exhaustion | Medium | Low | Monitoring, auto-scale plan | IT |
| R-07 | Security breach | High | Low | HTTPS, encryption, RBAC, audit log | IT |

---

## 9. Assumptions & Constraints

### 9.1 Assumptions
1. Owner dan staff bersedia menggunakan sistem digital
2. Internet tersedia stabil di lokasi toko
3. VPS yang ada cukup untuk 1-2 cabang pertama
4. Payment gateway (BCA + Midtrans) bisa diintegrasikan
5. Budget development tersedia sesuai estimasi

### 9.2 Constraints
1. VPS saat ini: 1 vCPU, 961 MB RAM (perlu upgrade)
2. Domain sudah ada: `beautynshine.web.id` (Cloudflare)
3. Timeline: 8 minggu untuk MVP
4. Team: 1 developer (full-stack Python)
5. Compliance: PPN 11% harus otomatis

---

## 10. Approval

| Role | Name | Signature | Date |
|---|---|---|---|
| Owner | _____________ | ________ | ____/____/____ |
| Manager | _____________ | ________ | ____/____/____ |
| System Analyst | _____________ | ________ | ____/____/____ |

---

*Document ini adalah property Beauty & Shine. Distribusi terbatas untuk stakeholder yang terlibat.*
