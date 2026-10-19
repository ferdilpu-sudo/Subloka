package app.subloka.feature.export

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.PrimaryAction
import app.subloka.core.designsystem.SecondaryAction
import app.subloka.core.domain.*

@Composable
fun ExportScreen(
    segments: List<CaptionSegment>,
    sourceLanguage: SourceLanguage,
    demoMode: Boolean,
    busy: Boolean,
    pending: Boolean,
    documents: List<SrtDocument>,
    saved: Set<Int>,
    message: String?,
    onPrepare: (SrtExportMode) -> Unit,
    onSave: (Int) -> Unit,
    onBack: () -> Unit,
    videoReady: Boolean,
    videoRendering: Boolean,
    videoMessage: String?,
    videoProgress: Int?,
    onRender: (SrtExportMode) -> Unit,
    onSaveVideo: () -> Unit,
    onCancelVideo: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var mode by rememberSaveable { mutableStateOf(SrtExportMode.BOTH) }
    val translationComplete = segments.isNotEmpty() && segments.all {
        it.translationStatus == TranslationStatus.CURRENT && it.translationText.isNotBlank() &&
            it.translationSourceRevision == it.sourceRevision
    }
    val locked = busy || pending
    val blocked = mode != SrtExportMode.SOURCE && !translationComplete
    Column(modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)) {
        SecondaryAction("Kembali ke editor", onBack, enabled = !locked)
        Text("Ekspor subtitle", style = MaterialTheme.typography.headlineSmall)
        if (demoMode) Text("Proyek demo — file berisi contoh caption.")
        Text("SRT menyimpan teks dan timing. Font, warna, dan style tidak disertakan pada SRT. MP4 menanamkan subtitle ke video.")
        ExportRadio("Asli (${sourceLanguage.label})", mode == SrtExportMode.SOURCE, !locked) { mode = SrtExportMode.SOURCE }
        ExportRadio("Terjemahan (${sourceLanguage.target.label})", mode == SrtExportMode.TRANSLATION, !locked) { mode = SrtExportMode.TRANSLATION }
        ExportRadio("Keduanya (SRT: dua file; MP4: dua bahasa)", mode == SrtExportMode.BOTH, !locked) { mode = SrtExportMode.BOTH }
        if (blocked) Text("Lengkapi atau perbarui terjemahan sebelum ekspor. Pilihan Asli tetap tersedia.", color = MaterialTheme.colorScheme.error)
        PrimaryAction("Siapkan SRT", { onPrepare(mode) }, enabled = !locked && !blocked && segments.isNotEmpty(), modifier = Modifier.fillMaxWidth())
        HorizontalDivider()
        Text("Video MP4", style = MaterialTheme.typography.titleMedium)
        Text("SDR · sisi terpanjang maksimal 1280 piksel · style dari editor. Render tetap berjalan saat berpindah aplikasi atau layar mati. Setelah selesai, buka aplikasi untuk memilih lokasi simpan.")
        SecondaryAction("Render MP4", { onRender(mode) }, enabled = !demoMode && !locked && !blocked && segments.isNotEmpty(), modifier = Modifier.fillMaxWidth())
        if (videoRendering) {
            Text(videoProgress?.let { "Render $it%" } ?: "Render sedang berjalan…")
            SecondaryAction("Hentikan render", onCancelVideo)
        }
        videoMessage?.let { Text(it) }
        if (videoReady) SecondaryAction("Simpan MP4 hasil render", onSaveVideo, enabled = !locked, modifier = Modifier.fillMaxWidth())
        HorizontalDivider()
        if (busy) LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
        message?.let { Text(it) }
        if (documents.isNotEmpty()) {
            Text("File yang sudah disiapkan", style = MaterialTheme.typography.titleMedium)
            Text("Pilih lokasi untuk setiap file. Gunakan penyimpanan perangkat agar tetap offline.")
            documents.forEachIndexed { index, document ->
                SecondaryAction(if (index in saved) "Simpan lagi: ${document.name}" else "Simpan: ${document.name}",
                    { onSave(index) }, enabled = !locked, modifier = Modifier.fillMaxWidth())
            }
        }
    }
}

@Composable
private fun ExportRadio(label: String, selected: Boolean, enabled: Boolean, onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth().heightIn(min = 48.dp)
        .selectable(selected, enabled = enabled, role = Role.RadioButton, onClick = onClick),
        verticalAlignment = Alignment.CenterVertically) {
        RadioButton(selected, onClick = null, enabled = enabled)
        Text(label, modifier = Modifier.padding(start = 12.dp))
    }
}
