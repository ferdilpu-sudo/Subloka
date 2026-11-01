# UI-AUTOCAP-MOBILE-001 — Adaptasi UI/UX AutoCap Desktop ke SubLoka Android

Tanggal: 2026-11-01
Sumber referensi: `ferdilpu-sudo/AutoCap-Desktop` (WinUI/XAML) dan `ferdilpu-sudo/Subloka` (Jetpack Compose).
Baseline Android: `main@5514e1a73e0dc698ece04acd3860aba7236216c9`, owner-accepted Beta #310.

## Temuan berbasis kode

AutoCap Desktop:
- `src/AutoCap.App/App.xaml` memiliki reusable title/subtitle/section/card/navigation styles; kartu 12px radius dan tipografi berjenjang.
- `src/AutoCap.App/MainWindow.xaml` memisahkan Home dari Editor, menonjolkan impor video dan Recent projects, serta memakai local-first status.
- `docs/MILESTONE-10.5.md` mengutamakan selected navigation, satu CTA utama, progressive disclosure setup, konsistensi spacing, aksesibilitas dan tidak memenuhi layar dengan tombol.

SubLoka:
- `feature/projects/ProjectsScreen.kt` sudah menampilkan proyek, privasi/lisensi, dan satu CTA Proyek baru yang melekat di bawah. Hierarki kartu lama hampir rata dan tidak mengelompokkan status sebagai metadata khusus.
- `feature/editor/EditorScreen.kt` sudah memisahkan Caption / Timing / Style dan mendukung compact/expanded preview; jangan mengubah alur engine.
- `.agents/design.md` secara eksplisit menetapkan **tidak ada bottom navigation di MVP**, **caption = hero**, video sebagai konteks, dan preview compact yang tidak boleh menindih editor.

## Klasifikasi kebutuhan
- P2 visual polish/consistency: hierarki judul, sekunder, pemisahan call-to-action, dan scan metadata proyek.
- P2 usability friction: status proyek yang tidak memiliki perlakuan visual terpisah.
- P1 guardrail: CTA tetap terjangkau di 320×480dp/150% font dan setelah scrolling 30 proyek; privacy/lisensi dan proyek lama tetap berfungsi.
- Tidak ada bukti kebutuhan mengganti informasi arsitektur atau menambah halaman utama.

## Adaptasi tahap 1: Home / Projects

MUST:
1. Header proyek dengan hierarki brand / title / subtitle dan kontrol Privasi dan lisensi yang tetap bekerja.
2. Panel Mulai dari video, menjelaskan alur video → caption → editor tanpa mengklaim model selalu siap.
3. Proyek terbaru sebagai section, nama dan berkas asli, bahasa/durasi/resolusi, waktu edit, status.
4. Tepat satu tombol utama Proyek baru tetap dapat diakses pada layar kecil atau daftar panjang.
5. Semantik buka proyek serta ID dan callback lama tidak berubah; proyek contoh tetap ditandai sebagai contoh.

SHOULD:
- Reuse `SubLokaColors`, typografi Material3, border tonal dan radius sederhana (bukan menyalin gaya WinUI mentah).
- Status disampaikan lewat teks, bukan warna saja.

COULD (tahap mendatang, perlu review UI):
- Editor caption-first yang makin ringkas, navigasi workspace yang lebih jelas, preview tidak menguasai tinggi layar, dan header save/export yang konsisten.
- Layar setup/model/processing/export dengan pemisahan section/status dan progresif disclosure.
- Jangan menyalin sidebar desktop ke navigasi mobile atau menambah bottom tabs tanpa bukti riset.

## Implementasi dan pengujian

Changed:
- `feature/projects/src/main/java/app/subloka/feature/projects/ProjectsScreen.kt`: visual hierarchy, card metadata, status surface, CTA tunggal tetap terjangkau.
- `app/src/androidTest/java/app/subloka/ProjectsScreenTest.kt`: regresi panel, section, dan exactly-one primary CTA.
- UI callbacks, database schema, engine libraries, model files, Room records, signing, SRT/MP4 pipeline: **tidak berubah**.

Validation:
- Static review: intended one `PrimaryAction("Proyek baru")`, existing project callbacks and privacy route retained.
- Android Compose instrumentation, UI snapshot on Sony SO-03L, keyboard/landscape, font scale, TalkBack: **PENDING**, not claimed PASS.
- No public release or merge to main without passing CI plus UI acceptance.

## Acceptance and next checkpoint
Owner should review visuals and compact interactions on Sony SO-03L before approving broader AutoCap-inspired redesign. Reference source is private; keep source text excerpts confined to needed comparison, do not publish a copy of the proprietary desktop UI. Continue with editor only after home visual/interaction direction is accepted.
