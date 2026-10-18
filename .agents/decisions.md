# Catatan Keputusan

Status keputusan: ACCEPTED = kebutuhan/keputusan telah disepakati; PROPOSED = arah rancangan menunggu tinjauan atau bukti; SUPERSEDED = diganti ADR baru, tidak dihapus. ACCEPTED tidak berarti sudah diimplementasikan/diuji. Evidence runtime berada di testing.md.

| ID | Keputusan | Status | Dasar / konsekuensi |
|---|---|---|---|
| ADR-001 | Android editor caption video | ACCEPTED | Pengguna memilih editor caption video, bukan live caption |
| ADR-002 | Seluruh proses konten offline, tanpa API berbayar | ACCEPTED | Instruksi pengguna; model disiapkan sekali, tidak ada fallback cloud |
| ADR-003 | Bilingual EN↔ID dengan timing bersama | ACCEPTED | Audio English → English+Indonesia dan sebaliknya |
| ADR-004 | Satu file satu tanggung jawab, tanpa batas baris | ACCEPTED | Struktur berdasar kohesi, bukan kuota baris |
| ADR-005 | Task/dependency/checkpoint/DoD serta docs update wajib | ACCEPTED | DONE mensyaratkan bukti dan dokumentasi sinkron |
| ADR-006 | Status dibuat, diuji, belum terverifikasi dipisah | ACCEPTED | Tidak menyamakan kode ada dengan fitur terbukti |
| ADR-007 | Native Kotlin/Compose dan Room | PROPOSED | Fokus Android, integrasi native/media lokal; versi final T02 |
| ADR-008 | whisper.cpp multilingual untuk ASR | PROPOSED | RAM, WER dan latensi wajib benchmark T10 |
| ADR-009 | ML Kit on-device EN↔ID | PROPOSED | Kualitas dialog, readiness, ketentuan SDK dan trafik perlu diperiksa |
| ADR-010 | Media3 untuk playback dan ekspor | PROPOSED | Timed bilingual overlay dan codec diuji T14 |
| ADR-011 | Tanpa akun/server, proyek lokal | ACCEPTED | Sesuai kebutuhan offline; backup cloud tidak masuk MVP |
| ADR-012 | UI lebih dahulu, lalu engine lokal, lalu integrasi | ACCEPTED | Fake UI tidak diklaim sebagai fitur AI selesai |
| ADR-013 | Satu video dan satu job berat aktif | PROPOSED | Menjaga lingkup dan RAM; batch/multitrack tidak diperlukan MVP |
| ADR-014 | Unduhan awal model diperbolehkan | ACCEPTED | User memilih offline tanpa biaya API; setup model eksplisit sebelum alur offline |
| ADR-015 | Subtitle per segmen, SRT asli/terjemahan terpisah | ACCEPTED | Dua bahasa berbagi timing; karaoke per kata/style SRT tidak dijanjikan |
| ADR-016 | Produk diarahkan sebagai focused bilingual caption editor, bukan general video editor | ACCEPTED | Audit UX + permintaan update paket; caption menjadi hero dan video hanya konteks |
| ADR-017 | Editor hanya memiliki workspace utama Caption, Timing, Style | ACCEPTED | Mengurangi beban kognitif; Caption default, timeline hanya fokus pada Timing |
| ADR-018 | Translation adalah state/action kontekstual, bukan workspace utama | ACCEPTED | Status stale/missing/current/failed melekat pada caption; menghindari mode keempat yang redundant |
| ADR-019 | Import/Processing/Export adalah flow/state project, bukan destination global | ACCEPTED | IA lebih dangkal; tidak ada kebutuhan bottom navigation pada MVP |
| ADR-020 | UI adaptif berdasarkan available window size; portrait 9:16 memiliki bounded preview | ACCEPTED | Editor harus tetap usable pada compact/expanded/keyboard; orientation saja tidak cukup |
| ADR-021 | Discipline audit UI memakai kategori defect dan severity P0–P3 | ACCEPTED | Mencegah aesthetic preference menyamar sebagai requirement dan mengutamakan blocker/friction |
| ADR-022 | Nama kerja produk **SubLoka**; applicationId sementara `app.subloka.caption` | ACCEPTED | Pendek, mudah diucapkan, mengomunikasikan subtitle + lokal; ID masih boleh berubah sebelum distribusi publik |
| ADR-023 | Baseline Android frontend memakai AGP 9.4.0 / Gradle 9.6.0 / Kotlin 2.3.21 / compile-target 37 / min 26 | ACCEPTED | Versi stabil saat eksekusi; minSdk 26 tetap mencakup perangkat uji Android 11 dan mengurangi kompatibilitas lama |
| ADR-024 | Frontend T04–T07 memakai fake adapter dan disclosure `DEMO` permanen sampai engine nyata terhubung | ACCEPTED | Memungkinkan validasi flow tanpa mengarang keberhasilan ASR/translation/export |
| ADR-025 | T10 membandingkan whisper.cpp v1.9.4 multilingual `tiny` dan `base`; synthetic smoke tidak boleh menutup CP4 | ACCEPTED | Upstream Android merekomendasikan tiny/base; model dipin dengan SHA-256; keputusan final menunggu WER/resource perangkat fisik |
| ADR-026 | T10 mengevaluasi ML Kit Translation 17.0.3 EN↔ID dengan explicit model readiness | ACCEPTED | EN/ID didukung on-device; input diproses lokal, tetapi SDK dapat melakukan model/update/metrics traffic sehingga disclosure privasi harus presisi |
| ADR-027 | Fixture ASR CP4 memakai Google FLEURS dev split EN/ID yang dipin; clean = durasi tipikal, challenging = long-utterance | ACCEPTED | Audio manusia + reference tersedia untuk kedua bahasa; challenging dilaporkan terpisah dan tidak diklaim sebagai uji noise/overlap/aksen |
| ADR-028 | Tahan promosi kandidat Argos ID→EN 1.9 ke Android setelah Full30; pertahankan ML Kit sampai ada bukti kualitas baru | PROPOSED | Pilot10 PROMISING (+2) tidak bertahan di Full30: Argos 21/30 = ML Kit 21/30, tambahan20 Argos 13/20 vs ML Kit 15/20; review menandai risiko kesalahan kritis. Bukan ambang FAIL Full30 yang ditentukan sebelumnya; perlu persetujuan jika memilih berhenti definitif/menjalankan holdout. CP4 tetap BLOCKED |

## Rationale keputusan teknis

ADR-007: native dipilih sebagai arah karena hanya Android yang diminta dan pemrosesan memerlukan decoder, lifecycle dan JNI. Cross-platform menambah lapisan yang belum dibutuhkan. Tidak memilih versi toolchain dari ingatan; pin versi yang berhasil dibangun.

ADR-008: pilih model multilingual, karena English-only tidak memenuhi bahasa Indonesia. Kandidat model kecil dibandingkan pada dataset EN/ID, bukan langsung mengunci model besar. Jika benchmark gagal, opsi sah ialah optimasi, model lokal lain, atau penyesuaian dukungan dengan persetujuan; tidak boleh beralih ke API tanpa permintaan pengguna.

ADR-009: translation lokal harus dinilai untuk dialog informal, negasi, nama dan angka. Koreksi manual selalu tersedia. “Tanpa biaya API” bukan klaim hasil translation setara layanan cloud atau SDK bebas dari ketentuan distribusi.

ADR-028 (PROPOSED, hasil Full30 2026-10-10): Penilai resmi Windows mencatat Argos/ML Kit sama-sama 21 ACCEPT dari 30 (net 0), 20 tambahan Argos 13/20 versus ML Kit 15/20 (net -2). Review terpisah mengidentifikasi kasus id-ab-13 (kepastian/negasi) dan id-ab-25 (mata uang). Dengan tidak adanya peningkatan agregat dan adanya risiko makna, kandidat Argos tidak direkomendasikan untuk promosi Android saat ini. Ini rekomendasi produk/rekayasa, bukan FAIL berdasarkan threshold Full30 baru atau persetujuan pengguna. Holdout baru hanya diperlukan bila promosi kandidat hendak dipertimbangkan kembali. Pertahankan artefak audit dan ML Kit baseline.

ADR-010: shared layout diperlukan agar preview dan video tidak berbeda. Overlay statis saja tidak membuktikan subtitle bertiming; T14 wajib membuktikan pergantian teks per timestamp. Codec/resolusi akhir mengikuti kemampuan nyata perangkat.

ADR-012: seluruh dokumen fase boleh dirancang sekarang; implementasi mengikuti checkpoint. Untuk aplikasi ini istilah backend berarti adapter penyimpanan dan engine lokal, bukan server.

## Rationale keputusan UX v0.2

ADR-016 sampai ADR-021 adalah guardrail produk, bukan sekadar preferensi visual. Dampaknya:

- Home sederhana dengan recent project + New Project.
- Tidak ada bottom navigation pada MVP.
- New Project menggabungkan import dan language source.
- Processing ditampilkan dalam konteks project.
- Caption adalah workspace default setelah generation.
- Timeline/detail timing tidak memenuhi workspace Caption.
- Translation stale/missing/current/failed muncul di segmen dan dapat diringkas untuk bulk action.
- Style tidak berkembang menjadi editor efek video.
- T03/CP2 harus membuktikan compact, expanded, keyboard, error, empty, stale, dan export states sebelum UI produksi.

Perubahan terhadap interaction model ini memerlukan ADR pengganti, bukan improvisasi saat implementasi.

## Pertanyaan terbuka dan pemilik penyelesaian

| ID | Pertanyaan | Task | Dampak jika belum terjawab |
|---|---|---|---|
| OQ01 | Nama produk/package ID final? | T01–T02 | **Sebagian terjawab:** SubLoka dipakai sebagai nama kerja dan `app.subloka.caption` sebagai ID sementara; brand/package baru final saat release packaging |
| OQ02 | HP target, RAM/OS dan perangkat tes yang tersedia? | T01 | **Baseline:** Sony SO-03L Android 11 sebagai perangkat primer yang pernah tersedia; RAM/koneksi aktual dan perangkat tambahan masih perlu verifikasi saat device test |
| OQ03 | Durasi/resolusi video paling sering? | T01/T10 | Belum ada profil penggunaan aktual; benchmark wajib memakai fixture 30 dtk / 2 mnt / 10 mnt, 720p dan 1080p, portrait + landscape sebelum batas dukungan diklaim |
| OQ04 | Model ASR mana yang memenuhi akurasi dan resource? | T10 | Tiny/base berhasil functional smoke; pilihan final tetap terbuka sampai benchmark manusia/perangkat fisik CP4 |
| OQ05 | Apakah translation lokal memenuhi kualitas dialog EN/ID? | T10/T12 | ML Kit readiness + bidirectional smoke PASS; kualitas 30 segmen per arah masih wajib sebelum CP4 |
| OQ06 | Versi SDK/native, min SDK, ABI, runner background? | T02/T13 | Build/lifecycle harus diverifikasi sesuai versi pilihan |
| OQ07 | Input codec/HDR/VFR dan profil ekspor yang didukung? | T09/T14 | Tampilkan unsupported yang jelas; tidak menjanjikan semua format |
| OQ08 | Distribusi APK/model, lisensi/atribusi dan metadata SDK? | T10/T16 | Rilis tertahan jika kebutuhan distribusi tidak terpenuhi |
| OQ09 | Breakpoint/window size Compose final dan ukuran preview compact? | T03/T04 | Harus ditentukan lewat wireframe/prototype dan device/window test, bukan angka arbitrer |
| OQ10 | Nama produk/brand visual dan app icon? | Setelah interaction model stabil | Tidak menghalangi T01–T04; jangan mencampur branding dengan usability gate |

## Template ADR baru

```text
ID / tanggal / status:
Konteks dan masalah:
Pilihan yang dibandingkan:
Keputusan dan alasan:
Konsekuensi terhadap scope, data, UI, resource:
Task dan dokumen terdampak:
Bukti / referensi:
Persetujuan jika diperlukan:
Menggantikan ADR:
```

Keputusan lama tidak dihapus ketika berubah; tandai SUPERSEDED dan tautkan ADR pengganti. Jangan menandai PROPOSED menjadi ACCEPTED hanya karena kode telanjur ditulis.


## ADR-029 — T11 foreground prototype exception / ACCEPTED / 2026-10-12
User explicitly authorized `lanjut` to real Whisper Base integration after reviewing unmet quality gates. CP4 remains BLOCKED and its thresholds/baselines are unchanged. T11 may implement a foreground-only prototype; this is not approval of release, cloud fallback, translation or export completion. Use pinned whisper.cpp v1.9.4 (peeled commit 927cfce34f31707e17f2bff35c349632fb9e2c3a), multilingual Base and existing SHA. Bundle JNI library, not an executable downloaded to writable app storage. Provision model through explicit import or download.

Prototype scope: videos up to 10 minutes, bounded 30-second non-overlapping windows, source text/timestamps only, blank translations MISSING, source-only preview. Cancel when Activity stops (rotation handled by ViewModel), no background completion/resume promise. No overlap means no duplicated inference region; boundary word loss and low-volume speech need device evaluation. Model remains loaded once per job; CPU only. Stage captions in memory and publish transactionally only into an empty project at matching content revision; new imports use new UUIDs and do not overwrite the legacy demo. The complete T11 acceptance including boundary quality and physical JNI evaluation remains pending until measured.


## ADR-030 — T12 foreground translation prototype / ACCEPTED / 2026-10-13
User reported successful Indonesian transcription, then explicitly said `lanjut` after the proposed offline Indonesia↔English integration and manual-edit protection. This authorizes T12 prototype work despite incomplete T11 physical acceptance and CP4 BLOCKED; it is not quality acceptance or release approval.
Use the existing pinned ML Kit 17.0.3 adapter. Model checking does not download; an explicit model-setup action provisions EN/ID with Wi-Fi selected by default. Editor offers translation of missing/stale machine captions, all eligible or one selected. Current and manually authored translations are preserved; replacing a manual translation automatically is not exposed in this increment. Flush editor saves before entering the translation flow and lock editing/project switching during a job. Publish each successful segment through existing Room source-revision/manual-origin CAS; completed translations survive failure/cancellation and retry only processes remaining eligible segments. No durable PENDING state or unverified resume claims. SDK task cancellation means stop awaiting/applying results, not a promise to abort an already started model download. Keep the existing foreground-only lifecycle. Full physical bilingual/quality validation stays pending.


## ADR-031 — Bounded SRT export prototype / ACCEPTED / 2026-10-13
User confirmed translation success and safe manual corrections, then authorized `lanjut` after the proposed subtitle export. Implement FR10 before full T13/CP5 under this bounded exception; CP4 remains BLOCKED. MP4 rendering and durable job recovery remain pending. Export immutable saved caption snapshots as UTF-8 SRT, original, translation, or two separate language files. Floor microseconds to milliseconds consistently and reject collapsed intervals, overlap, empty cues, and invalid translations. Document picker saves each file separately, reporting per-file results, never atomic pair success. Android providers do not promise atomic external writes: failure may leave a partial newly created document, so attempt deletion and clearly report if cleanup fails. Process death cannot be called success. No database migration.


## ADR-032 — Foreground MP4 prototype / ACCEPTED / 2026-10-13
User said `lanjut saja` after SRT delivery and the explicit MP4 limitation. Authorizes implementing the next export increment; does not attest physical SRT success or close CP4/CP5. Use pinned Media3 Transformer/effect 1.11.1, H.264/AAC MP4, SDR only, <=10-minute input, aspect-preserving even dimensions capped at 1280 longest side without upscaling. One shared Android Canvas/StaticLayout subtitle painter serves preview and export, with source/translation/dual mode, language order, existing size/outline/background/bottom settings and explicit overflow rejection. Keep source immutable and recheck fingerprint before render. Foreground rendering cancels on Activity stop except rotation; private staging never offered before Transformer completion plus output track/duration validation. Document picker only after ready; per-file save completion and partial cleanup follow SRT policy. No background completion/resume or full T13 acceptance claim. Stale staging from process death is cleaned on exporter initialization, with a retry message. Physical codecs/readability/performance remain gates, not assumed from emulator.

## ADR-033 — Speech detection for generated-caption timing (2026-10-15)
User-reported incorrect generated timing was reproduced exactly (18/18 text/time entries) using pinned Base and whisper.cpp, after source/render PCM identity was verified. Fixed 10s chunk retry introduced unrelated repeated text and was rejected. Enable built-in Silero VAD in pinned whisper.cpp before decoding each existing 30s window; use its original-time mapping getters and add the outer window offset only once. Keep default VAD parameters, pinned Base/beam settings, no context, cancellation and atomic caption publication. Reject punctuation-only generated segments, but do not deduplicate legitimate repeated speech. VAD is speech detection, not forced alignment or a guarantee of accurate transcription. Local sample improved from 18 to 6 segments with the long repetition removed; exact word/timing ground truth and Android physical behavior remain unverified.
Provision Silero 6.2.0 separately and explicitly (download missing models or import Base/VAD independently); no media upload and no automatic model download. Pin HF revision 9ffd54a1e1ee413ddf265af9913beaf518d1639b and SHA256 2aa269b785eeb53a82983a20501ddf7c1d9c48e33ab63a41391ac6c9f7fb6987; measured 885098 bytes, MIT, license bundled. Existing verified Base stays installed, caption generation requires both verified models. Existing project captions/edits are not regenerated automatically; use a new project for comparison. CP4 baseline/gates unchanged. Possible missed quiet speech, chunk-boundary splits and remaining word errors require broader evaluation.


## ADR-034 — Accuracy-oriented offline caption candidate / ACCEPTED for prototype / 2026-10-16
User requests replacement of the poor caption engine. Evaluate new weights locally before integration. Maleo Base-ID/Small-ID q8 both collapse the main dialogue into a single 13.69s caption with this decoder; do not promote based on read-speech publisher WER. Select multilingual Whisper Large-v3 Turbo q5_0 as the new explicit setup default, with existing Base available as a lightweight alternative. This replaces recognition weights, not the pinned whisper.cpp runtime. Native Silero and original-clock mapping remain. No cloud inference or media upload.
Turbo source: ggerganov/whisper.cpp revision 5359861c739e955e79d9a303bcbc70fb988958b1, ggml-large-v3-turbo-q5_0.bin, 574041195 bytes, SHA256 394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2, MIT (existing Whisper license). Keep separate model files, explicit download/import and selection-dependent readiness. Use exact descriptor byte limits, atomic checksum publication, no silent fallback. Model selection resets readiness and is frozen during a job; saved captions never regenerated automatically.
This is a user-authorized quality-oriented prototype, not CP4 acceptance. Sony runtime/memory/thermal impact and human-verified words/timing are unmeasured. Existing RTF/WER gates unchanged; do not promise real-time or broad quality improvement. UI discloses size/performance uncertainty before download and permits choosing Base. Default selection is Turbo each app launch; no Room migration.


## ADR-035 — Offline translation replacement (2026-10-17)
Accepted for prototype under user request for a better translation model. TranslateGemma 4B Q4_K_M is default; ML Kit remains an explicit lightweight alternative, never a hidden fallback. Pinned quantization mradermacher/translategemma-4b-it-GGUF revision d37868f759d2f817a43d28dd80cf9f982ffa62fd, 2489909760 bytes, SHA256 81200d03e843d2ec1ece6eeafe7d13cb6e5211e1fcd336ade55790b683a08330. llama.cpp 2a667032dc788c3a071d538e0b572e45a3f12731; CPU 4 threads, context1024, greedy output256, source384 tokens. Official translation template, literal source-token parsing, no truncated output publication. Disable extra weight buffers to limit duplicate memory. Hide both engines' static ggml symbols to prevent cross-version interposition.
Gemma Terms (2026-04-01) and Prohibited Use Policy bundled with notice; user must explicitly review/accept before model import/download/use. SHA/exact-size verified atomic install; offline import; explicit Wi-Fi-only default. Large download and unverified device RAM/runtime disclosed. One heavy operation at a time. Explicit unchecked option may replace current MACHINE output, always preserving MANUAL, source/time and source-revision CAS. Existing Room schema unchanged. Prior-session local candidate probes were reported but artifacts were lost during workspace maintenance; reconstructed implementation must earn new test evidence. No CP4/production/quality promotion. User reports Turbo transcription improvement; no formal WER claim.


## ADR-036 — Durable translation recovery
Accepted under user authorization, 2026-10-17. Reuse Room v1 processing_jobs for TRANSLATE logical work, with a versioned inline JSON checkpoint in checkpoint_ref (exception to earlier file-reference-only design). Contains only pending segment IDs/source revisions and total, not copied transcript text. Persist job before inference; publish each accepted caption and remove its pending item within one Room transaction. Failed rows remain pending; manual/changed/deleted rows are skipped. Startup marks orphan RUNNING jobs INTERRUPTED. Explicit resume creates a new attempt from validated pending rows with the same pinned engine/model; prior attempt is CANCELLED/SUPERSEDED, never relabeled successful. Discard clears the resumable attempt only, never caption results. Resume cannot silently change engine or include unrelated/new captions. Foreground-only cancellation remains; no claim of continuous background execution or ASR/MP4 resume. No table/column migration, model unchanged.


## ADR-037 — Owner-held prototype signing / 2026-10-18
User update failure and model backup/restore demonstrate temporary CI debug keys are unsuitable for an update channel. Introduce one owner-generated private PKCS12 bundle in repository Actions Secrets, backed up on the owner's PC. Never commit a key or derive it deterministically. Manual Android CI on the authorized prototype branch re-signs the exact tested APK only after build/emulator gates; PRs never receive signing secret. Missing/malformed key or certificate mismatch fails without fallback. Separate stable signed artifact from test-only debug APK. CI versionCode is workflow run_number (local2); preserve workflow numbering. Existing package ID/storage unchanged; debug capability retained for prototype diagnostics. No old private key is available; first migration is not promised in-place. Production signing/release is a later decision. Source: https://developer.android.com/tools/apksigner and https://cli.github.com/manual/gh_secret_set reviewed2026-10-18.


## ADR-038 — Service-owned ASR / 2026-10-18
User confirms translation resume and requests continuation after migration. ASR now belongs to a started foreground service, not Activity ViewModel. Start only from explicit visible UI action, with mediaProcessing type on API35+ and dataSync local-file processing on API29–34. Notification opens app and cancels the identified job. Partial wake lock is bounded and released on all terminal paths. Service owns separate Room handle and native pipeline, keeps atomic publishGenerated CAS, and is START_NOT_STICKY. Application-process state reconnects recreated UI; process death is not resumable and never auto-restarts model work. Translation and MP4 still cancel on background. Cancellation after successful atomic commit reports saved completion. No schema or engine change. References reviewed2026-10-18: developer.android.com/develop/background-work/services/fgs/service-types, /launch, /timeout.
