package app.subloka.feature.export

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
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
import app.subloka.core.designsystem.SubLokaColors
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
    var mode by rememberSaveable { mutableStateOf(SrtExportMode.SOURCE) }
    var mp4 by rememberSaveable { mutableStateOf(false) }
    // Reattached renders must expose their progress and save action immediately.
    LaunchedEffect(videoRendering, videoReady) {
        if (videoRendering || videoReady) mp4 = true
    }
    val translationComplete = segments.isNotEmpty() && segments.all {
        it.translationStatus == TranslationStatus.CURRENT && it.translationText.isNotBlank() &&
            it.translationSourceRevision == it.sourceRevision
    }
    val locked = busy || pending || videoRendering
    val blocked = mode != SrtExportMode.SOURCE && !translationComplete
    val canPrepare = !locked && !blocked && segments.isNotEmpty()
    val nextUnsavedSrt = SrtSaveActions.nextUnsaved(documents, saved)
    Column(modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            TextButton(onClick = onBack, enabled = !locked) { Text("Kembali ke editor") }
            Text("Ekspor caption", style = MaterialTheme.typography.headlineSmall)
            if (demoMode) Text("Proyek contoh · SRT berisi contoh caption. Render MP4 tersedia pada proyek video.")
            ExportSection("Format hasil") {
                SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                    SegmentedButton(selected = !mp4, onClick = { mp4 = false }, enabled = !locked,
                        shape = SegmentedButtonDefaults.itemShape(0, 2)) { Text("SRT") }
                    SegmentedButton(selected = mp4, onClick = { mp4 = true }, enabled = !locked,
                        shape = SegmentedButtonDefaults.itemShape(1, 2)) { Text("MP4") }
                }
                Text(if (mp4) "Video dengan caption tertanam, memakai gaya dari editor."
                    else "File teks dan timing untuk pemutar atau editor video. Gaya, font, dan warna tidak disertakan.",
                    style = MaterialTheme.typography.bodySmall, color = SubLokaColors.TextSecondary)
            }
            ExportSection("Bahasa caption") {
                Column(Modifier.selectableGroup()) {
                    ExportRadio("Asli (${sourceLanguage.label})", mode == SrtExportMode.SOURCE, !locked) { mode = SrtExportMode.SOURCE }
                    ExportRadio("Terjemahan (${sourceLanguage.target.label})", mode == SrtExportMode.TRANSLATION, !locked) { mode = SrtExportMode.TRANSLATION }
                    ExportRadio("Keduanya", mode == SrtExportMode.BOTH, !locked) { mode = SrtExportMode.BOTH }
                }
                if (mode == SrtExportMode.BOTH) Text(
                    if (mp4) "Dua bahasa ditampilkan dalam satu video."
                    else "Dua file SRT disiapkan dan disimpan satu per satu.",
                    style = MaterialTheme.typography.bodySmall, color = SubLokaColors.TextSecondary,
                )
            }
            // Preserve the provenance advisory added by PR #2. SOURCE-only export shows no warning.
            if (mode != SrtExportMode.SOURCE) {
                val warnings = TranslationOrigins.exportWarnings(segments)
                if (warnings.isNotEmpty()) {
                    Surface(
                        color = SubLokaColors.Surface,
                        shape = RoundedCornerShape(12.dp),
                        border = BorderStroke(1.dp, SubLokaColors.Warning.copy(alpha = 0.6f)),
                    ) {
                        Column(Modifier.fillMaxWidth().padding(14.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("Asal terjemahan", style = MaterialTheme.typography.titleSmall,
                                color = SubLokaColors.Warning)
                            warnings.forEach { warning ->
                                Text(warning, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }
            }
            if (segments.isEmpty()) Text("Belum ada caption. Kembali ke editor untuk membuat caption.", color = MaterialTheme.colorScheme.error)
            else if (blocked) Text("Lengkapi atau perbarui terjemahan di editor, atau pilih Asli untuk melanjutkan.", color = MaterialTheme.colorScheme.error)
            ExportSection(if (mp4) "Hasil video" else "File SRT") {
                if (mp4) {
                    Text("SDR · sisi terpanjang maksimal 1280 piksel. Render tetap berjalan saat berpindah aplikasi atau layar mati.", style = MaterialTheme.typography.bodySmall)
                    if (videoRendering) {
                        Text(videoProgress?.let { "Render $it%" } ?: "Render sedang berjalan…", style = MaterialTheme.typography.titleMedium)
                        LinearProgressIndicator(Modifier.fillMaxWidth())
                    }
                    videoMessage?.let { Text(it) }
                    if (videoReady) {
                        Text("Hasil render tersedia", style = MaterialTheme.typography.titleMedium)
                        Text("Tekan Simpan MP4 untuk memilih lokasi. Membatalkan pemilih lokasi tidak menghapus hasil render.")
                        Text("Pilihan bahasa baru berlaku setelah render ulang. Render ulang mengganti hasil sementara yang belum disimpan.", style = MaterialTheme.typography.bodySmall)
                        SecondaryAction("Render ulang dengan pilihan ini", { onRender(mode) }, enabled = canPrepare && !demoMode, modifier = Modifier.fillMaxWidth())
                    }
                } else {
                    message?.let { Text(it) }
                    if (documents.isNotEmpty()) {
                        Text("SRT siap disimpan", style = MaterialTheme.typography.titleMedium)
                        Text("${documents.indices.count { it in saved }} dari ${documents.size} file tersimpan.",
                            style = MaterialTheme.typography.bodyMedium)
                        Text("Nama bahasa mengikuti file SRT yang sudah disiapkan. Pilih lokasi penyimpanan untuk setiap file.",
                            style = MaterialTheme.typography.bodySmall, color = SubLokaColors.TextSecondary)
                        documents.forEachIndexed { index, document ->
                            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text(document.name, style = MaterialTheme.typography.bodyMedium)
                                Text(
                                    when {
                                        index in saved -> "Tersimpan"
                                        index == nextUnsavedSrt -> "Berikutnya disimpan"
                                        else -> "Belum disimpan"
                                    },
                                    color = if (index in saved) SubLokaColors.TextSecondary else SubLokaColors.Primary,
                                    style = MaterialTheme.typography.labelMedium,
                                )
                                // The next pending file uses the fixed primary action below. Other
                                // files remain individually selectable, even out of order.
                                if (index in saved) {
                                    SecondaryAction(
                                        SrtSaveActions.resaveLabel(document, index),
                                        { onSave(index) }, enabled = !locked,
                                        modifier = Modifier.fillMaxWidth(),
                                    )
                                } else if (index != nextUnsavedSrt) {
                                    SecondaryAction(
                                        SrtSaveActions.saveLabel(document, index),
                                        { onSave(index) }, enabled = !locked,
                                        modifier = Modifier.fillMaxWidth(),
                                    )
                                }
                            }
                        }
                        TextButton(onClick = { onPrepare(mode) }, enabled = canPrepare) {
                            Text("Siapkan SRT lagi")
                        }
                        Text("Menyiapkan ulang mengganti daftar hasil yang siap disimpan, bukan file yang sudah disimpan di perangkat.",
                            style = MaterialTheme.typography.bodySmall, color = SubLokaColors.TextSecondary)
                    }
                }
            }
            if (busy && !videoRendering) LinearProgressIndicator(Modifier.fillMaxWidth())
            if (pending) Text("Pilih lokasi penyimpanan. Jika dibatalkan, hasil tetap tersedia untuk disimpan lagi.")
        }
        when {
            videoRendering -> SecondaryAction("Hentikan render", onCancelVideo, modifier = Modifier.fillMaxWidth())
            mp4 && videoReady -> PrimaryAction("Simpan MP4", onSaveVideo, enabled = !locked, modifier = Modifier.fillMaxWidth())
            mp4 -> PrimaryAction("Render MP4", { onRender(mode) }, enabled = canPrepare && !demoMode, modifier = Modifier.fillMaxWidth())
            documents.isNotEmpty() && nextUnsavedSrt != null -> {
                val index = nextUnsavedSrt
                PrimaryAction(
                    SrtSaveActions.saveLabel(documents[index], index),
                    { onSave(index) }, enabled = !locked, modifier = Modifier.fillMaxWidth(),
                )
            }
            documents.isNotEmpty() -> PrimaryAction(
                "Selesai — kembali ke editor", onBack,
                enabled = !locked, modifier = Modifier.fillMaxWidth(),
            )
            else -> PrimaryAction("Siapkan SRT", { onPrepare(mode) }, enabled = canPrepare, modifier = Modifier.fillMaxWidth())
        }
    }
}


/** Native mobile grouping: no new export mode, callbacks, or data transformations. */
@Composable
private fun ExportSection(title: String, content: @Composable ColumnScope.() -> Unit) {
    Surface(
        color = SubLokaColors.Surface,
        shape = RoundedCornerShape(12.dp),
        border = BorderStroke(1.dp, SubLokaColors.SurfaceHigh),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            content()
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
