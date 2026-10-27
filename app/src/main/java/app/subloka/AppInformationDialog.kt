package app.subloka

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Offline access to privacy information and the notices actually bundled in this APK. */
@Composable
internal fun AppInformationDialog(onClose: () -> Unit) {
    val context = LocalContext.current
    val uriHandler = LocalUriHandler.current
    var linkError by remember { mutableStateOf(false) }
    fun openReference(url: String) {
        linkError = runCatching { uriHandler.openUri(url) }.isFailure
    }
    var selected by rememberSaveable { mutableStateOf<String?>(null) }
    val notices by produceState<Map<String, String>?>(null, context) {
        value = withContext(Dispatchers.IO) {
            try {
                context.assets.list("licenses").orEmpty().sorted().associateWith { name ->
                    context.assets.open("licenses/$name").bufferedReader().use { it.readText() }
                }
            } catch (_: Exception) { emptyMap() }
        }
    }
    fun back() { if (selected != null) selected = null else onClose() }
    Dialog(onDismissRequest = ::back) {
        Surface(shape = MaterialTheme.shapes.large) {
            Column(Modifier.fillMaxWidth().fillMaxHeight(0.9f).padding(16.dp)) {
                Text(if (selected == null) "Privasi dan lisensi" else "Dokumen lisensi",
                    style = MaterialTheme.typography.titleLarge)
                key(selected) {
                    LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        if (selected != null) {
                            item { Text(selected.orEmpty(), style = MaterialTheme.typography.titleSmall) }
                            item { Text(selected?.let { notices?.get(it) } ?: "Dokumen belum tersedia. Kembali dan coba lagi.") }
                        } else {
                            item { Text("Pemrosesan di perangkat", style = MaterialTheme.typography.titleMedium) }
                            item { Text("Video, caption dan terjemahan diproses di perangkat. Proyek disimpan dalam aplikasi. Unduhan model memerlukan jaringan; setelah model siap, alur utama dapat digunakan offline.") }
                            item { Text("Jaringan dan ML Kit", style = MaterialTheme.typography.titleMedium) }
                            item { Text("Unduhan model menghubungi penyedia berkas. Alternatif ML Kit memproses teks secara lokal, tetapi SDK Google dapat mengirim metrik perangkat, aplikasi, penggunaan dan bahasa, serta menghubungi Google untuk pembaruan. Memilih Gemma bukan jaminan tidak adanya seluruh trafik SDK.") }
                            item { Text("Referensi: developers.google.com/ml-kit/terms dan developers.google.com/ml-kit/android-data-disclosure") }
                            item { Text("Penyedia terjemahan", style = MaterialTheme.typography.titleMedium) }
                            item { Text("Opsi ML Kit menggunakan Google Translate untuk terjemahan di perangkat. TranslateGemma adalah model terpisah. Label pada caption menunjukkan penyedia yang tercatat; hasil lama tanpa catatan penyedia tidak ditebak. Hasil yang dikoreksi diberi label diedit manual.") }
                            item { TextButton(onClick = { openReference("https://cloud.google.com/translate") }) { Text("Tentang Google Translate — buka browser") } }
                            item { TextButton(onClick = { openReference("https://developers.google.com/ml-kit/language/translation/translation-terms") }) { Text("Ketentuan terjemahan ML Kit — buka browser") } }
                            if (linkError) item { Text("Browser tidak dapat dibuka. Referensi: cloud.google.com/translate", color = MaterialTheme.colorScheme.error) }
                            item { Text("Penyimpanan dan cadangan", style = MaterialTheme.typography.titleMedium) }
                            item { Text("SRT/MP4 disimpan ke lokasi pilihanmu. Penyedia cloud dapat menyinkronkan hasil. Backup Android dinonaktifkan; ekspor bukan cadangan proyek lengkap. Menghapus data atau uninstall dapat menghilangkan proyek dan model. Gunakan pembaruan tanpa uninstall.") }
                            item { Text("Diagnostik lokal mencatat tahap, durasi dan kegagalan. Periksa log sebelum membagikannya. Jangan unggah video, transkrip pribadi atau kunci penandatanganan ke laporan publik.") }
                            item { Text("Lisensi yang disertakan", style = MaterialTheme.typography.titleMedium) }
                            item { Text("Dokumen berikut tersedia offline. Daftar ini berisi berkas atribusi yang dibundel, bukan sertifikasi kelengkapan seluruh dependensi. Hasil otomatis tetap perlu diperiksa.") }
                            if (notices == null) item { Text("Memuat dokumen…") }
                            else if (notices.isNullOrEmpty()) item { Text("Dokumen lisensi tidak dapat dibuka. Tutup lalu coba lagi.") }
                            items(notices?.keys?.toList().orEmpty(), key = { it }) { name ->
                                TextButton(onClick = { selected = name }, modifier = Modifier.fillMaxWidth()) { Text(name) }
                            }
                        }
                    }
                }
                TextButton(onClick = ::back, modifier = Modifier.fillMaxWidth()) {
                    Text(if (selected == null) "Tutup" else "Kembali ke informasi")
                }
            }
        }
    }
}
