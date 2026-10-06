package app.subloka.feature.export

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.DemoBadge
import app.subloka.core.designsystem.PrimaryAction
import app.subloka.core.designsystem.SecondaryAction
import app.subloka.core.designsystem.SubLokaColors
import app.subloka.core.domain.CaptionSegment
import app.subloka.core.domain.TranslationStatus

private enum class CaptionExportMode { DUAL, SOURCE, TRANSLATION }

@Composable
fun ExportScreen(
    segments: List<CaptionSegment>,
    onBack: () -> Unit,
    onDone: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var mode by remember { mutableStateOf(CaptionExportMode.DUAL) }
    val translationComplete = segments.all { it.translationStatus == TranslationStatus.CURRENT }
    val blocked = mode != CaptionExportMode.SOURCE && !translationComplete

    Column(
        modifier = modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("‹", style = MaterialTheme.typography.headlineSmall, modifier = Modifier.clickable(onClick = onBack))
            Text("Export", style = MaterialTheme.typography.headlineSmall)
        }
        DemoBadge()

        Text("Caption", style = MaterialTheme.typography.titleMedium)
        ExportRadio("English + Indonesia", mode == CaptionExportMode.DUAL, translationComplete) { mode = CaptionExportMode.DUAL }
        ExportRadio("Original", mode == CaptionExportMode.SOURCE, true) { mode = CaptionExportMode.SOURCE }
        ExportRadio("Translation", mode == CaptionExportMode.TRANSLATION, translationComplete) { mode = CaptionExportMode.TRANSLATION }

        if (blocked) {
            Surface(color = SubLokaColors.Error.copy(alpha = 0.12f), shape = RoundedCornerShape(8.dp)) {
                Text(
                    "Export bilingual/translation diblokir karena ada terjemahan missing, stale, atau gagal. Original-only tetap tersedia.",
                    modifier = Modifier.padding(12.dp),
                    color = SubLokaColors.Error,
                )
            }
        }

        Text("Quality", style = MaterialTheme.typography.titleMedium)
        Text("1080p · kandidat demo, dukungan codec belum diverifikasi", color = SubLokaColors.TextSecondary)

        PrimaryAction(
            text = "Export Video",
            onClick = onDone,
            enabled = !blocked,
            modifier = Modifier.fillMaxWidth(),
        )
        SecondaryAction("Export .SRT", onClick = onDone, modifier = Modifier.fillMaxWidth(), enabled = !blocked)
        Text(
            "Tombol demo tidak membuat file media. Renderer dan pipeline export baru masuk T14.",
            color = SubLokaColors.TextSecondary,
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@Composable
private fun ExportRadio(label: String, selected: Boolean, enabled: Boolean, onClick: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().clickable(enabled = enabled, onClick = onClick).padding(vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        RadioButton(selected = selected, onClick = onClick, enabled = enabled)
        Text(label, color = if (enabled) SubLokaColors.TextPrimary else SubLokaColors.TextSecondary)
    }
}
