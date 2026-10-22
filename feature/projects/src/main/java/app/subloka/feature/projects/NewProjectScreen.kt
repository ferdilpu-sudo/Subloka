package app.subloka.feature.projects

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.PrimaryAction
import app.subloka.core.designsystem.SubLokaColors
import app.subloka.core.domain.MediaDescriptor
import app.subloka.core.domain.SourceLanguage

@Composable
fun NewProjectScreen(
    selectedMedia: MediaDescriptor?, mediaLoading: Boolean, mediaError: String?,
    onPickVideo: () -> Unit, onBack: () -> Unit, onContinue: (SourceLanguage) -> Unit,
    modifier: Modifier = Modifier,
) {
    var sourceLanguage by rememberSaveable { mutableStateOf(SourceLanguage.ENGLISH) }
    val validVideo = selectedMedia != null && selectedMedia.durationUs <= 600_000_000L
    Column(modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            TextButton(onClick = onBack, enabled = !mediaLoading) { Text("Kembali") }
            Text("Proyek baru", style = MaterialTheme.typography.headlineSmall)
            Text("Langkah 1 dari 2 · Video dan bahasa", color = SubLokaColors.TextSecondary)
            Text("Pilih video maksimal 10 menit. Periksa hasil caption sebelum digunakan.", style = MaterialTheme.typography.bodyMedium)
            Surface(color = SubLokaColors.Surface, shape = RoundedCornerShape(12.dp)) {
                Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(if (mediaLoading) "Memeriksa video…" else selectedMedia?.displayName ?: "Belum ada video",
                        style = MaterialTheme.typography.titleMedium)
                    Text(when {
                        mediaLoading -> "Memastikan video dan audionya dapat dibaca."
                        selectedMedia != null -> mediaSummary(selectedMedia)
                        else -> "Pilih satu video dari perangkat. Video asli tetap utuh."
                    }, color = SubLokaColors.TextSecondary)
                    if (mediaLoading) LinearProgressIndicator(Modifier.fillMaxWidth())
                    if (selectedMedia != null) TextButton(onClick = onPickVideo, enabled = !mediaLoading) { Text("Ganti video") }
                }
            }
            if (mediaError != null) Text(mediaError, color = SubLokaColors.Error)
            if (selectedMedia != null) {
                if (!validVideo) Text("Video melebihi 10 menit. Tekan Ganti video untuk memilih video yang lebih pendek.", color = SubLokaColors.Error)
                Text("Bahasa yang diucapkan", style = MaterialTheme.typography.titleMedium)
                Column(Modifier.selectableGroup()) {
                    LanguageRadio("Inggris", sourceLanguage == SourceLanguage.ENGLISH, !mediaLoading) { sourceLanguage = SourceLanguage.ENGLISH }
                    LanguageRadio("Indonesia", sourceLanguage == SourceLanguage.INDONESIA, !mediaLoading) { sourceLanguage = SourceLanguage.INDONESIA }
                }
                Text("Caption dibuat dalam bahasa audio yang dipilih. Terjemahan dapat dibuat nanti dari editor.", color = SubLokaColors.TextSecondary)
            }
        }
        PrimaryAction(
            text = when {
                mediaLoading -> "Memeriksa video…"
                selectedMedia != null -> if (mediaError != null) "Coba lanjut lagi" else "Lanjut ke model"
                else -> "Pilih video"
            },
            onClick = { if (selectedMedia == null) onPickVideo() else onContinue(sourceLanguage) },
            enabled = !mediaLoading && (selectedMedia == null || validVideo),
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

private fun mediaSummary(media: MediaDescriptor): String {
    val rotated = media.rotationDegrees == 90 || media.rotationDegrees == 270
    val width = if (rotated) media.heightPx else media.widthPx
    val height = if (rotated) media.widthPx else media.heightPx
    val orientation = when { height > width -> "Vertikal"; width > height -> "Horizontal"; else -> "Persegi" }
    return "%02d:%02d · %d × %d · %s".format(media.durationUs / 60_000_000, media.durationUs / 1_000_000 % 60, width, height, orientation)
}

@Composable
private fun LanguageRadio(label: String, selected: Boolean, enabled: Boolean, onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth().heightIn(min = 48.dp)
        .selectable(selected = selected, enabled = enabled, role = Role.RadioButton, onClick = onClick)
        .padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        RadioButton(selected = selected, onClick = null, enabled = enabled)
        Text(label, modifier = Modifier.padding(start = 12.dp))
    }
}
