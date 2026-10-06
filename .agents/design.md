# Desain Interaksi dan Tampilan

Status: **arah UX v0.2 dikunci sebagai baseline**, tetapi belum ada UI Android, prototype teruji, atau screenshot produksi. Nama/ikon produk belum dikunci. T03 wajib menerjemahkan spesifikasi ini menjadi wireframe/prototype state dan CP2 wajib meninjaunya sebelum UI produksi.

## 1. Design intent

Produk harus terasa seperti **focused offline bilingual caption workspace**: dark, tenang, profesional, dan cepat dipahami. Jangan meniru editor video umum. Pengguna datang untuk memperbaiki caption, bukan mengatur track video.

Hierarki produk:

```text
Caption      = hero / pekerjaan utama
Video        = context / bahan pengecekan
Timeline     = contextual / muncul saat timing
Translation  = state + action / bukan workspace utama
Style        = secondary tool
Export       = final action
```

Prinsip desain:

- Cognitive clarity > visual spectacle.
- Satu primary action jelas per layar.
- Recognition over recall: label bahasa dan status ditulis, bukan hanya warna/icon.
- Progressive disclosure: kontrol lanjutan muncul saat dibutuhkan.
- Calm feedback: error penting terlihat; status normal tidak memenuhi toolbar.
- Jangan redesign pola yang sudah jelas hanya untuk terlihat berbeda.

## 2. Information architecture

### 2.1 Destination utama

```text
Home / Projects
├── New Project flow
├── Existing Project → Editor
└── Settings
    ├── Offline Models
    ├── Storage
    └── Preferences
```

Tidak ada bottom navigation pada MVP.

### 2.2 Flow project baru

```text
New Project
  ↓
Pilih video
  ↓
Pilih source language
  ↓
Pastikan model siap
  ↓
Generate caption
  ↓
Processing state
  ↓
Editor / Caption
```

Import dan Process bukan tab/destination permanen. Export dibuka dari editor sebagai final action/sheet/screen kontekstual.

## 3. Arah visual

Arah visual: **graphite + soft indigo + minimal tonal surfaces**. Hindari neon creator UI, glassmorphism berlebihan, gradient dekoratif, dan kartu bertumpuk tanpa hierarchy.

| Token semantic | Baseline proposal |
|---|---|
| `bg.canvas` | #0F1115 |
| `bg.surface` | #181B21 |
| `bg.surfaceHigh` | #21252D |
| `text.primary` | #F5F7FA |
| `text.secondary` | #AEB6C5 |
| `action.primary` | #A7B5FF |
| `action.onPrimary` | #101216 |
| `state.success` | #7EDBA6 |
| `state.warning` | warm amber, final token ditentukan setelah contrast check |
| `state.error` | #FFB4AB |
| Spacing | 4, 8, 12, 16, 24, 32 dp |
| Radius | 8 dp controls, 12 dp panels, 16 dp prominent sheets bila perlu |
| UI type baseline | 12 label/meta, 14 body/control, 18 section/title; harus mengikuti font scale |

Token adalah baseline T03/T04, bukan bukti contrast lulus. Warna tidak boleh menjadi satu-satunya pembeda status.

## 4. Layar dan tanggung jawab

| Area | Tanggung jawab | Primary action |
|---|---|---|
| Home / Projects | recent project + empty state | New Project |
| New Project | pilih video, metadata, source language | Buat Caption |
| Model setup | siapkan model offline hanya saat perlu | Siapkan Offline / Retry |
| Processing state | stage/progress/cancel/recovery | Batalkan atau lanjut setelah selesai |
| Editor / Caption | review dan koreksi teks bilingual | edit selected caption |
| Editor / Timing | koreksi sinkronisasi | adjust start/end |
| Editor / Style | atur presentasi subtitle | preview/update style |
| Export | pilih output valid | Export Video / Export SRT |
| Settings | model/storage/preferences | aksi sesuai setting |

## 5. Home / Projects

Home bukan analytics dashboard. Tampilkan identitas app, Settings, daftar recent project, dan satu primary action **New Project**.

Project card minimal menampilkan thumbnail bila tersedia, title/source name, language direction, duration, dan last edited. Jangan memenuhi card dengan status teknis yang tidak membantu pemilihan project.

Empty state:

```text
Belum ada project

Pilih video untuk membuat caption
bilingual secara offline.

[ Pilih video ]
```

Tidak membutuhkan ilustrasi besar. Bila model belum siap, model setup muncul ketika user memulai flow, bukan sebagai hambatan permanen pada home kecuali ada alasan hasil riset.

## 6. Model setup

Copy harus memakai bahasa pengguna, bukan nama engine internal.

Contoh struktur:

```text
Siapkan Caption Offline

Aplikasi membutuhkan model bahasa agar
caption dan translation dapat diproses
di perangkat.

Video dan audio tidak diunggah.

Model caption       [Ready / Download]
English–Indonesia   [Ready / Download]

[ Siapkan Offline ]
```

- Tampilkan ukuran hanya jika diketahui nyata.
- Download failure memiliki retry.
- Storage shortage memiliki tindakan pemulihan.
- Jangan menampilkan “Whisper”, “ML Kit”, JNI, package, atau istilah engine kecuali di area developer/about yang memang perlu.

## 7. New Project

New Project menggabungkan import + source language. Target language otomatis.

Struktur compact:

```text
New Project

[ video thumbnail / metadata ]
Traveling.mp4
03:42 • 1080p

Bahasa audio
(●) English
( ) Indonesia

Caption akan dibuat:
English + Indonesia

[ Buat Caption ]
```

Jika video belum dipilih, primary action adalah **Pilih video**. Setelah video valid, primary action menjadi **Buat Caption**. Jangan menampilkan dua primary button bersamaan.

## 8. Processing sebagai state

Setelah **Buat Caption**, user tetap berada dalam konteks project. Tampilkan preview/identity project dan status pemrosesan.

```text
Membuat caption di perangkat

Menyiapkan audio       ✓
Mengenali ucapan       ●
Menerjemahkan          ○

128 / 284 segmen

[ Batalkan ]
```

Aturan:

- Gunakan progress numerik hanya jika denominator/percent benar-benar diketahui.
- Jika tidak, gunakan stage + indeterminate.
- Selesai stage ditandai dengan teks/icon selain warna.
- Interrupted menampilkan checkpoint dan aksi resume/retry yang benar-benar didukung engine.
- Cancel tidak menampilkan sukses semu.
- Bila app memakai fake adapter sebelum engine ada, beri label **Demo** yang tidak dapat disalahartikan sebagai inference nyata.

## 9. Editor: interaction model

### 9.1 Struktur global

Top app bar:

```text
‹  Project title                 ↶  ↷  Export
```

Save feedback muncul sementara:

- `Menyimpan…` saat flush/transaction berjalan.
- `✓ Tersimpan` boleh tampil singkat lalu hilang.
- `Gagal menyimpan · Coba lagi` tetap terlihat sampai dipulihkan.

Jangan menampilkan “Saved” permanen sebagai dekorasi.

Setelah hasil generation tersedia, workspace default adalah **Caption**.

Workspace switcher:

```text
Caption     Timing     Style
```

Jangan menambah `Translation` sebagai tab keempat pada MVP.

### 9.2 Preview

Preview menunjukkan oriented video content rectangle + subtitle renderer yang sama secara aturan dengan export.

- Video portrait tidak boleh memakai tinggi penuh hanya karena aspect ratio 9:16.
- T03 harus menentukan maximum preview height per compact state.
- Preview harus cukup besar untuk mengecek timing/position, tetapi workspace caption harus tetap terlihat tanpa scroll ekstrem.
- Playback controls minimum: play/pause, current time/duration, seek behavior yang dapat diakses.

## 10. Workspace Caption — default

Tujuan: **baca → dengarkan → koreksi → lanjut**.

Tidak menampilkan full timeline sebagai pusat UI.

Segment card/list minimal:

```text
01:24.20 – 01:28.10

ENGLISH · ASLI
This place is absolutely beautiful.

INDONESIA · TERJEMAHAN
Tempat ini benar-benar indah.

✓ Terjemahan terbaru
```

Selected segment membuka inline editor atau supporting pane/bottom editor tanpa dialog modal yang tidak perlu.

Selected editor:

```text
ENGLISH · ASLI
[ This place is absolutely beautiful. ]

INDONESIA · TERJEMAHAN
[ Tempat ini benar-benar indah. ]

01:24.20                         01:28.10

[ Split ]                  [ Merge next ]
```

Rules:

- Memilih segmen seek ke start.
- Field selalu dilabeli language + role (`ASLI`, `TERJEMAHAN`).
- Edit source menandai translation `Perlu diperbarui`.
- Edit translation manual membuat origin MANUAL sesuai schema.
- Jangan membuka full-screen dialog hanya untuk edit teks pada keadaan normal.
- Long text/readability warning tampil kontekstual, bukan sebagai alarm global.

## 11. Translation state/action

Translation bukan workspace. Gunakan state per segment dan ringkasan bila perlu.

Per segment:

```text
INDONESIA · TERJEMAHAN
Perlu diperbarui

[ text lama tetap terlihat ]

[ Terjemahkan ulang ]
```

Jika banyak stale:

```text
3 terjemahan perlu diperbarui
[ Perbarui semua ]
```

Jika translation pernah diedit manual, retranslate wajib menjelaskan bahwa versi manual akan diganti dan meminta tindakan eksplisit. Jangan overwrite otomatis.

State yang harus punya tampilan: MISSING, PENDING, CURRENT, STALE, FAILED.

## 12. Workspace Timing

Timeline dan precision controls menjadi fokus hanya di workspace Timing.

Minimum:

```text
[ preview ]

─────────│────────────────
        00:24.420

║ caption 12 ║
          ║ caption 13 ║

Start                         End
00:24.20                  00:28.10

[-100] [-10]        [+10] [+100]
```

- Drag handles boleh digunakan.
- Drag **tidak boleh menjadi satu-satunya cara**; sediakan direct time input atau nudge.
- Minimum interval, overlap, clamp duration mengikuti schema/domain.
- Timing dua bahasa tetap satu interval.
- Pemilihan caption mempertahankan continuity dengan Caption workspace.

## 13. Workspace Style

Style adalah secondary tool. Gunakan progressive disclosure.

MVP:

- Display: Dual / Original / Translation.
- Order: source first / translation first.
- Font asset bundled/local yang didukung.
- Size per language.
- Color per language.
- Outline.
- Optional background.
- Alignment.
- Position group.
- Safe-area guide sebagai panduan.

Jangan masukkan ke MVP tanpa perubahan scope: puluhan font, gradient, shadow editor kompleks, keyframe, caption animation, karaoke, per-word effects.

## 14. Subtitle bilingual dan readability

- Default source: near-white; translation: warm/light accent yang lolos contrast pada video dengan outline/background yang sesuai.
- Label bahasa/role tetap digunakan di editor; jangan mengandalkan warna.
- Source di atas, translation di bawah secara default; user dapat tukar urutan.
- Kedua teks berada dalam satu kelompok relatif terhadap **video content rectangle**, bukan letterbox.
- Posisi default center-bottom dengan margin bawah baseline 12%; T03/T14 menguji safe rendering.
- Font size disimpan sebagai ratio terhadap oriented frame height, bukan dp layar.
- Hard maximum rancangan: 2 baris per bahasa. Ideal: 1 baris + 1 baris bila konten memungkinkan.
- Jika terlalu panjang/cepat dibaca, tampilkan warning seperti `Teks mungkin terlalu cepat dibaca` dan tindakan `Split segment`/ubah size; jangan truncate diam-diam.
- Preview dan export menggunakan aturan layout/font yang sama; font harus tersedia/bundled secara konsisten.

## 15. Keyboard behavior

Keyboard adalah state desain wajib, terutama pada video portrait.

Normal compact:

```text
Preview (bounded)
Playback
Workspace switcher
Caption list/editor
```

Keyboard aktif:

```text
Compact preview / optional minimized preview
Selected caption editor
Active field tetap terlihat
Keyboard
```

Rules:

- Jangan biarkan IME menutup selected field atau action penting.
- Preview boleh diperkecil, bukan editor yang dipaksa menjadi area beberapa piksel.
- Scroll focus ke field aktif bila perlu.
- Back pertama menutup keyboard sesuai pola platform; back berikutnya mengikuti navigation behavior.

## 16. Adaptive layout

Desain mengikuti available window size, bukan `portrait/landscape` saja.

### Compact

```text
[ Preview ]
[ Playback ]
[ Caption | Timing | Style ]
[ Workspace panel ]
```

### Expanded / supporting pane

```text
┌────────────────────┬────────────────────────┐
│                    │ Caption/Timing/Style   │
│       VIDEO        │                        │
│                    │ selected editor/list   │
│     playback       │                        │
└────────────────────┴────────────────────────┘
```

- T03 menentukan breakpoint/window-size strategy yang cocok dengan Compose/toolchain aktual.
- Jangan menduplikasi domain logic untuk compact vs expanded; hanya presentation/composition berubah.
- Split-screen/foldable behavior tidak boleh diasumsikan dari orientation.

## 17. Export UX

Export dibuka dari top app bar/final action.

Urutan sederhana:

```text
Export

VIDEO
(●) Video + subtitle
( ) Video tanpa subtitle [jika memang dibutuhkan scope]

Caption
(●) English + Indonesia
( ) English
( ) Indonesia

Quality
(●) 1080p [jika didukung]
( ) 720p

[ Export Video ]

Subtitle files
[ Export .SRT ]
```

- Jangan tampilkan codec/bitrate/fps sebagai default MVP kecuali user memang harus memilih.
- Opsi unsupported/blocked punya alasan jelas.
- Dual/translation export diblokir bila required translation MISSING/STALE/FAILED sesuai PRD.
- Source-only tetap tersedia bila source valid.
- Export progress/failure/cancel adalah state nyata, bukan snackbar palsu.

## 18. State wajib

| Kondisi | Perilaku |
|---|---|
| Belum ada project | Empty state + satu action Pilih video/New Project |
| Belum ada model, jaringan mati | Jelaskan perlu unduhan awal; jangan fallback online |
| Model downloading | progress jika diketahui; retry/cancel sesuai kemampuan |
| Sedang process | stage nyata; progress tidak dibuat-buat; indeterminate bila total unknown |
| Tidak ada ucapan | hasil kosong jelas; tawarkan tambah subtitle manual jika fitur tersedia |
| Tanpa audio | error sebelum inference; editor manual boleh dibuka bila masuk scope |
| URI hilang | relink source; verifikasi kecocokan sebelum timing lama digunakan |
| Storage kurang | jelaskan ruang bila dapat dihitung; jangan hapus source otomatis |
| Process interrupted | status interrupted + checkpoint/retry/resume yang benar-benar didukung |
| Translation stale | text lama tetap terlihat + status + retranslate |
| Translation incomplete | dual/translation export disabled + alasan; source-only tersedia |
| Save failure | persistent recovery action; jangan meninggalkan layar seolah tersimpan |
| Keyboard aktif | compact preview + selected editor tetap terlihat |
| Long text/overflow | warning + tindakan; tidak truncate diam-diam |
| Hasil demo | label demo permanen; tidak menyimpan output palsu sebagai sukses |

## 19. Component inventory minimum

T03/T04 harus mendefinisikan komponen berdasarkan tanggung jawab, bukan membuat design-system abstrak tanpa kebutuhan:

- AppTopBar / ProjectTopBar.
- PrimaryButton / SecondaryButton / IconAction dengan states.
- ProjectCard.
- LanguageChoice.
- ModelStatusRow.
- ProcessingStageList.
- VideoPreviewFrame + SubtitleOverlay.
- PlaybackControls.
- WorkspaceSwitcher.
- CaptionSegmentRow/Card.
- BilingualTextEditor.
- TranslationStatusAction.
- TimingEditor / NudgeControls.
- StyleControlGroup.
- InlineStatus / ErrorRecovery.
- ExportOptionGroup.

Setiap komponen baru harus memiliki alasan reuse atau consistency yang nyata.

## 20. Acceptance criteria desain per area

### Home
- User langsung melihat recent projects dan primary action New Project.
- Tidak ada bottom navigation.
- Empty state dapat dipahami tanpa tutorial.

### New Project
- User dapat menjawab video apa yang dipilih, source language apa, dan output bilingual apa yang akan dibuat.
- Tidak ada pilihan target language yang redundant.

### Processing
- User dapat mengetahui apa yang sedang terjadi tanpa progress palsu.
- Cancel/interrupted/error punya recovery yang jelas.

### Caption
- User dapat menemukan, memilih, mendengar, mengedit source/translation, melihat stale state, split/merge, dan berpindah ke caption berikutnya tanpa membuka timeline penuh.

### Timing
- User dapat melakukan koreksi presisi tanpa mengandalkan drag saja.

### Style
- User dapat mengubah display/order/size/color/outline/background/position tanpa melihat kontrol video-editing di luar scope.

### Adaptive/keyboard
- 9:16 compact, 16:9 compact, landscape/window expanded, keyboard aktif, dan font scale besar tetap mempertahankan task utama.

### Export
- User memahami apa yang diekspor dan kenapa opsi tertentu blocked.

## 21. Gate CP2

T03 harus menghasilkan minimal:

1. IA final.
2. Primary user flow.
3. Compact portrait wireframe.
4. Compact landscape/wide wireframe.
5. Expanded/supporting-pane wireframe.
6. Keyboard-active state.
7. Caption workspace states.
8. Timing workspace states.
9. Style workspace states.
10. Processing/loading/error/interrupted states.
11. Export flow dan blocked states.
12. Component inventory + semantic token proposal.
13. Accessibility notes + focus/touch-target behavior.
14. Acceptance criteria mapping ke PRD.

CP2 **tidak lulus hanya karena visual terlihat bagus**. Reviewer harus dapat menjawab dengan jelas:

- bagaimana membuat project;
- bagaimana mengetahui source language;
- bagaimana memperbaiki caption;
- bagaimana memperbaiki translation;
- bagaimana mengatur timing;
- bagaimana mengubah style;
- bagaimana mengetahui stale translation;
- bagaimana export;
- apa yang terjadi bila job gagal/terputus;
- apa yang terjadi ketika keyboard terbuka atau ruang layar berubah.


## 22. T03 execution specification — SubLoka

Status: **interaction specification dibuat 2026-10-06**. Ini mengunci komposisi frontend demo; usability runtime tetap harus diuji pada T04–T07.

### 22.1 Navigation graph

```text
Projects
  ├─ New Project
  │    └─ Model Setup [hanya bila model belum ready]
  │         └─ Processing
  │              └─ Editor / Caption
  │                   ├─ Timing
  │                   ├─ Style
  │                   └─ Export
  └─ Recent Project ────────────────┘
```

Back behavior: Export → Editor; Editor → Projects; New Project → Projects. Processing cancel → Projects pada demo; engine nyata wajib mengikuti cleanup/recovery T13. Tidak ada bottom navigation.

### 22.2 Window strategy

- **Compact:** available width `< 840dp`. Preview, playback, workspace switcher, workspace panel disusun vertikal.
- **Expanded/supporting pane:** available width `≥ 840dp`. Video/context di kiri dan active workspace di kanan.
- `600dp` bukan navigation breakpoint terpisah pada MVP; medium window tetap memakai compact composition agar jumlah perilaku yang diuji tidak meledak tanpa manfaat.
- Preview normal compact maksimal **248dp**; ketika IME terlihat, preview maksimal **112dp**.
- Expanded preview mempertahankan aspect ratio konten dan tidak memaksa tinggi penuh. Hard cap runtime dapat dipoles setelah device test tanpa mengubah IA.

### 22.3 Compact portrait wireframe

```text
┌────────────────────────────────┐
│ ‹ Traveling        ↶ ↷ Export │
│ DEMO · engine belum terhubung  │
│ ┌────────────────────────────┐ │
│ │        VIDEO PREVIEW       │ │  max 248dp
│ │   source subtitle          │ │
│ │   translation subtitle     │ │
│ └────────────────────────────┘ │
│ ▶ 01:24.20              03:42 │
│ Caption     Timing      Style  │
│ ┌────────────────────────────┐ │
│ │ active workspace           │ │
│ │ selected editor / controls │ │
│ │ segment list when Caption  │ │
│ └────────────────────────────┘ │
└────────────────────────────────┘
```

### 22.4 Compact wide / landscape

Compact-wide tetap memakai struktur vertikal agar focus order dan keyboard behavior sama. Preview menggunakan lebar tersedia tetapi dibatasi tinggi; workspace mendapatkan sisa tinggi. Jika lebar mencapai 840dp, komposisi beralih ke supporting pane, bukan aturan orientation khusus.

### 22.5 Expanded/supporting pane

```text
┌──────────────────────────────────────────────────────┐
│ ‹ Traveling                         ↶ ↷ Export       │
│ DEMO                                                 │
├──────────────────────────┬───────────────────────────┤
│                          │ Caption | Timing | Style  │
│      VIDEO PREVIEW       │                           │
│                          │ active workspace          │
│      playback            │ selected editor/list     │
│                          │                           │
└──────────────────────────┴───────────────────────────┘
```

Sumber state sama dengan compact; hanya composition yang berubah.

### 22.6 Keyboard-active state

```text
┌────────────────────────────────┐
│ app bar                         │
│ ┌────────────────────────────┐ │
│ │ compact video preview      │ │  max 112dp
│ └────────────────────────────┘ │
│ Caption | Timing | Style       │
│ ACTIVE BILINGUAL FIELD         │
│ active field + recovery action │
├────────────────────────────────┤
│            IME                 │
└────────────────────────────────┘
```

IME visibility mengurangi preview, bukan menghilangkan editor. Focused field wajib tetap dapat discroll ke area visible; back pertama mengikuti dismiss IME platform.

### 22.7 Caption interaction states

- Segment selected melakukan seek-to-start ketika media adapter nyata tersedia.
- Source field selalu `LANGUAGE · ASLI`; target selalu `LANGUAGE · TERJEMAHAN`.
- Edit source: translation status → `STALE`; teks lama tetap terlihat.
- Edit translation manual: status → `CURRENT`, origin → `MANUAL`.
- `MISSING`, `PENDING`, `CURRENT`, `STALE`, `FAILED` memiliki label teks/simbol, tidak hanya warna.
- Bulk stale summary muncul jika `staleCount > 0`.
- Split/Merge tersedia sebagai action eksplisit; implementasi domain menunggu T08.

### 22.8 Timing interaction states

Timing menampilkan contextual timeline, direct start/end value, dan nudge `-100/-10/+10/+100 ms`. Drag handle boleh ditambahkan setelah implementasi media tetapi tidak menggantikan input/nudge. Invalid interval/overlap wajib menampilkan error inline dan menolak commit domain pada T08.

### 22.9 Style interaction states

Kontrol awal: Dual/Original/Translation, ukuran per bahasa, outline, background, position. Order, alignment, dan color picker dipertahankan dalam inventory T06 tetapi tidak boleh berkembang menjadi keyframe/effect editor. Preview menggunakan style state yang sama dengan renderer kontrak T14.

### 22.10 Model, processing, dan recovery states

Model setup membedakan `NOT_READY`, `DOWNLOADING`, `READY`, `FAILED`, storage shortage, network unavailable-before-first-download. Engine terms tidak ditampilkan pada copy utama.

Processing state membedakan stage `WAITING`, `ACTIVE`, `COMPLETE`, `FAILED`; numeric progress hanya muncul bila denominator nyata. Demo memiliki tombol `Selesaikan demo` yang jelas bukan hasil inference.

Interrupted/resume belum disimulasikan sebagai keberhasilan karena kemampuan checkpoint engine belum dibuktikan.

### 22.11 Export states

Modes: Dual, Original, Translation. Dual/Translation disabled bila satu saja segment `MISSING`, `STALE`, atau `FAILED`; Original tetap tersedia. Export demo tidak menulis file. Quality `1080p` hanya label kandidat sampai T14 memverifikasi codec/resolution.

### 22.12 Empty/error/save/relink/long text

- Empty Projects: satu primary action New Project/Pilih video.
- Save failure: persistent inline recovery, bukan toast saja.
- URI lost: relink flow sebelum playback/process; matching source divalidasi di T09.
- Long text: warning inline + Split/size action; tidak truncate diam-diam.
- No audio/storage full/process failure: recovery action spesifik sesuai domain error code.

### 22.13 Component contract

Komponen yang benar-benar dipakai frontend demo: `PrimaryAction`, `SecondaryAction`, `DemoBadge`, Projects card, Language radio, Model status row, Processing stage list, VideoPreview, Workspace switcher, Caption editor/list, Timing workspace, Style workspace, Export options. Abstraksi tambahan ditolak sampai ada reuse/consistency need yang nyata.

### 22.14 Accessibility contract

- Semua action target minimum 48dp.
- Language/role selalu ditulis; status selalu memiliki teks/simbol selain warna.
- Focus order mengikuti visual order: app bar → preview/playback → workspace switcher → active panel.
- Precision timing memiliki alternatif terhadap gesture.
- Font scale besar boleh membuat halaman scroll; field aktif dan recovery action tidak boleh terpotong permanen.
- TalkBack labels final, contrast token final, keyboard navigation hardware, dan screenshot font-scale diuji saat runtime tersedia.

### 22.15 Mapping requirement

| Spec area | Requirement utama |
|---|---|
| Projects/New Project | FR02, journey import, no bottom nav |
| Model setup/offline disclosure | FR12, R03 |
| Processing states | FR03/FR04, R06/R08 |
| Caption + stale translation | FR05/FR06, R05 |
| Timing | FR07, timing invariant |
| Style/readability | FR08 |
| Export blocked/source-only | FR09/FR10 |
| Adaptive/IME/accessibility | NFR usability/accessibility, R14 |

T03 tidak membuktikan runtime usability. Ia menetapkan interaction contract agar implementasi frontend dapat dinilai tanpa improvisasi IA.
