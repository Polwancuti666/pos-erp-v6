# Contributing to POS-ERP V6

Terima kasih atas ketertarikan Anda untuk berkontribusi! Dokumen ini menjelaskan proses dan standar kontribusi untuk project POS-ERP Integration Engine V6.

---

## Branch Naming

Gunakan prefix berikut untuk branch Anda:

| Prefix | Kegunaan | Contoh |
|---|---|---|
| `feature/` | Fitur baru | `feature/payment-qris-callback` |
| `fix/` | Bug fix | `fix/sync-queue-retry-logic` |
| `hotfix/` | Fix urgent di production | `hotfix/checkout-null-pointer` |
| `docs/` | Dokumentasi | `docs/update-readme` |
| `refactor/` | Refactoring tanpa perubahan behavior | `refactor/extract-payment-service` |
| `test/` | Penambahan atau perbaikan test | `test/inventory-edge-cases` |

Format: `<prefix>/<short-description-kebab-case>`

---

## Commit Convention

Project ini mengikuti [Conventional Commits](https://www.conventionalcommits.org/).

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Kegunaan |
|---|---|
| `feat` | Fitur baru |
| `fix` | Bug fix |
| `docs` | Perubahan dokumentasi |
| `style` | Formatting, tidak mengubah kode |
| `refactor` | Refactoring kode |
| `test` | Penambahan/perbaikan test |
| `chore` | Maintenance (deps, CI, dll.) |
| `perf` | Performance improvement |

### Contoh

```
feat(checkout): add QRIS payment type support

- Implement QRIS callback verification
- Add QR code generation for payment
- Update PaymentType enum

Closes #42
```

```
fix(sync): handle network timeout during outbox flush

Previously, a network timeout during sync would leave items
in PENDING state without proper retry scheduling.
```

```
docs(readme): update installation instructions for Docker
```

---

## Pull Request Rules

1. **Branch dari `main`** — semua PR harus target `main`
2. **Satu fitur per PR** — jangan campur beberapa fitur/fix dalam satu PR
3. **Test harus pass** — semua test harus hijau sebelum merge
4. **Deskripsi jelas** — jelaskan apa yang diubah dan mengapa
5. **Link ke issue** — referensikan issue terkait (jika ada)
6. **Draft PR** — gunakan Draft PR untuk work-in-progress

### PR Template

```markdown
## Deskripsi
[Jelaskan perubahan yang dibuat]

## Tipe Perubahan
- [ ] Feature baru
- [ ] Bug fix
- [ ] Refactoring
- [ ] Dokumentasi
- [ ] Lainnya: ___

## Testing
- [ ] Unit test baru ditambahkan
- [ ] Semua test existing pass
- [ ] Manual testing dilakukan

## Checklist
- [ ] Code mengikuti style guide project
- [ ] Commit messages sesuai conventional commits
- [ ] Dokumentasi diupdate (jika diperlukan)
- [ ] Tidak ada hardcoded secret/credential
```

---

## Code Review Checklist

Reviewer akan memeriksa hal-hal berikut:

### Kode
- [ ] Kode mudah dibaca dan dipahami
- [ ] Tidak ada kode yang di-comment out tanpa penjelasan
- [ ] Error handling memadai
- [ ] Tidak ada magic numbers — gunakan konstanta
- [ ] Fungsi/method tidak terlalu panjang (idealnya < 50 baris)

### Arsitektur
- [ ] Perubahan sesuai dengan domain boundary yang ada
- [ ] Tidak melanggar prinsip modular monolith
- [ ] Business logic di layer yang tepat (domain, bukan controller)
- [ ] Repository pattern digunakan untuk data access

### Keamanan
- [ ] Tidak ada hardcoded credentials
- [ ] Input validasi dilakukan
- [ ] SQL injection dicegah (gunakan parameterized queries)
- [ ] HMAC signature diverifikasi untuk payment webhooks
- [ ] RBAC diperiksa untuk endpoint baru

### Testing
- [ ] Test coverage memadai untuk kode baru
- [ ] Edge cases ditest
- [ ] Test tidak bergantung pada test lain (isolated)
- [ ] Mock digunakan untuk external dependencies

### Performance
- [ ] Tidak ada N+1 query
- [ ] Database index dipertimbangkan untuk query baru
- [ ] Async digunakan untuk I/O-bound operations

---

## Development Setup

```bash
# 1. Fork dan clone
git clone https://github.com/your-username/pos-erp-v6.git
cd pos-erp-v6

# 2. Buat virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Copy env
cp .env.example .env

# 5. Jalankan test untuk memastikan semua OK
pytest

# 6. Buat branch baru
git checkout -b feature/your-feature-name
```

---

## Style Guide

- **Python:** Ikuti PEP 8, gunakan `black` untuk formatting
- **Type hints:** Wajib untuk semua function signatures
- **Docstrings:** Gunakan Google style docstrings
- **Naming:**
  - `snake_case` untuk variable dan function
  - `PascalCase` untuk class
  - `UPPER_SNAKE_CASE` untuk konstanta
- **Imports:** Group — stdlib, third-party, local (dipisah blank line)

---

## Pertanyaan?

Jika ada pertanyaan, buka [Discussion](https://github.com/your-org/pos-erp-v6/discussions) atau hubungi tim maintainer.

Terima kasih sudah berkontribusi! 🙏
