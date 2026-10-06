package app.subloka.feature.editor

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.SecondaryAction
import app.subloka.core.designsystem.SubLokaColors
import app.subloka.core.domain.CaptionSegment
import app.subloka.core.domain.TranslationStatus

@Composable
fun CaptionWorkspace(
    segments: List<CaptionSegment>,
    selectedId: String,
    onSelect: (String) -> Unit,
    onSourceChange: (String) -> Unit,
    onTranslationChange: (String) -> Unit,
    onRetranslate: () -> Unit,
    onSplit: () -> Unit,
    onMergeNext: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val selected = segments.first { it.id == selectedId }
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        val staleCount = segments.count { it.translationStatus == TranslationStatus.STALE }
        if (staleCount > 0) {
            Surface(color = SubLokaColors.Warning.copy(alpha = 0.12f), shape = RoundedCornerShape(8.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text("$staleCount terjemahan perlu diperbarui", color = SubLokaColors.Warning)
                    Text("Perbarui semua", color = SubLokaColors.Primary)
                }
            }
        }

        SelectedCaptionEditor(
            segment = selected,
            onSourceChange = onSourceChange,
            onTranslationChange = onTranslationChange,
            onRetranslate = onRetranslate,
            onSplit = onSplit,
            onMergeNext = onMergeNext,
        )

        Text("Segments", style = MaterialTheme.typography.titleSmall)
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(segments, key = { it.id }) { segment ->
                SegmentCard(segment = segment, selected = segment.id == selectedId, onClick = { onSelect(segment.id) })
            }
        }
    }
}

@Composable
private fun SelectedCaptionEditor(
    segment: CaptionSegment,
    onSourceChange: (String) -> Unit,
    onTranslationChange: (String) -> Unit,
    onRetranslate: () -> Unit,
    onSplit: () -> Unit,
    onMergeNext: () -> Unit,
) {
    Surface(color = SubLokaColors.Surface, shape = RoundedCornerShape(12.dp)) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("${segment.sourceLanguage.label.uppercase()} · ASLI", style = MaterialTheme.typography.labelMedium)
            OutlinedTextField(
                value = segment.sourceText,
                onValueChange = onSourceChange,
                modifier = Modifier.fillMaxWidth(),
                minLines = 2,
            )
            Text("${segment.sourceLanguage.target.label.uppercase()} · TERJEMAHAN", style = MaterialTheme.typography.labelMedium)
            if (segment.translationStatus == TranslationStatus.STALE) {
                Text("Perlu diperbarui", color = SubLokaColors.Warning, style = MaterialTheme.typography.labelMedium)
            }
            OutlinedTextField(
                value = segment.translationText,
                onValueChange = onTranslationChange,
                modifier = Modifier.fillMaxWidth(),
                minLines = 2,
            )
            if (segment.translationStatus == TranslationStatus.STALE) {
                SecondaryAction("Terjemahkan ulang", onRetranslate, modifier = Modifier.fillMaxWidth())
            }
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(formatTime(segment.startUs), color = SubLokaColors.TextSecondary)
                Text(formatTime(segment.endUs), color = SubLokaColors.TextSecondary)
            }
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                SecondaryAction("Split", onClick = onSplit, modifier = Modifier.weight(1f))
                SecondaryAction("Merge next", onClick = onMergeNext, modifier = Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun SegmentCard(segment: CaptionSegment, selected: Boolean, onClick: () -> Unit) {
    Surface(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        color = if (selected) SubLokaColors.SurfaceHigh else SubLokaColors.Surface,
        shape = RoundedCornerShape(10.dp),
    ) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text("${formatTime(segment.startUs)} – ${formatTime(segment.endUs)}", color = SubLokaColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
            Text("${segment.sourceLanguage.code} · ASLI", style = MaterialTheme.typography.labelSmall)
            Text(segment.sourceText)
            Text("${segment.sourceLanguage.target.code} · TERJEMAHAN", style = MaterialTheme.typography.labelSmall)
            Text(segment.translationText, color = SubLokaColors.TextSecondary)
            Text(translationLabel(segment.translationStatus), color = translationColor(segment.translationStatus), style = MaterialTheme.typography.labelSmall)
        }
    }
}

internal fun formatTime(us: Long): String {
    val totalMs = us / 1_000
    val minutes = totalMs / 60_000
    val seconds = (totalMs % 60_000) / 1_000
    val centis = (totalMs % 1_000) / 10
    return "%02d:%02d.%02d".format(minutes, seconds, centis)
}

private fun translationLabel(status: TranslationStatus): String = when (status) {
    TranslationStatus.MISSING -> "○ Terjemahan belum ada"
    TranslationStatus.PENDING -> "● Sedang diterjemahkan"
    TranslationStatus.CURRENT -> "✓ Terjemahan terbaru"
    TranslationStatus.STALE -> "! Perlu diperbarui"
    TranslationStatus.FAILED -> "! Terjemahan gagal"
}

private fun translationColor(status: TranslationStatus) = when (status) {
    TranslationStatus.CURRENT -> SubLokaColors.Success
    TranslationStatus.STALE -> SubLokaColors.Warning
    TranslationStatus.FAILED -> SubLokaColors.Error
    TranslationStatus.PENDING -> SubLokaColors.Primary
    TranslationStatus.MISSING -> SubLokaColors.TextSecondary
}
