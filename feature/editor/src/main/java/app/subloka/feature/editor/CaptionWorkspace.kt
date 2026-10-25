package app.subloka.feature.editor

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.ime
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.selected
import androidx.compose.material3.TextButton
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
    demoMode: Boolean = true,
    translationAvailable: Boolean = true,
    modifier: Modifier = Modifier,
) {
    val selectedIndex = segments.indexOfFirst { it.id == selectedId }
    val selected = segments[selectedIndex]
    val listState = rememberLazyListState()
    var listRequested by rememberSaveable { mutableStateOf(false) }
    BoxWithConstraints(modifier) {
        val keyboardVisible = WindowInsets.ime.getBottom(LocalDensity.current) > 0
        val showBoth = maxHeight >= 500.dp && !keyboardVisible
        Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            if (!showBoth) {
                TextButton(onClick = { listRequested = !listRequested }) {
                    Text(if (listRequested) "Kembali ke koreksi" else "Daftar caption (${segments.size})")
                }
            }
            if (showBoth || !listRequested) {
                Column(Modifier.weight(if (showBoth) 0.65f else 1f)
                    .verticalScroll(rememberScrollState())) {
                    CaptionNavigation(segments, selectedId, onSelect)
                    SelectedCaptionEditor(
                        segment = selected,
                        canMergeNext = selectedIndex < segments.lastIndex,
                        translationAvailable = translationAvailable,
                        demoMode = demoMode,
                        onSourceChange = onSourceChange,
                        onTranslationChange = onTranslationChange,
                        onRetranslate = onRetranslate,
                        onSplit = onSplit,
                        onMergeNext = onMergeNext,
                    )
                }
            }
            if (showBoth || listRequested) {
                LazyColumn(
                    modifier = Modifier.weight(if (showBoth) 0.35f else 1f).testTag("caption-list"),
                    state = listState,
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(segments, key = { "segment-${it.id}" }) { segment ->
                        SegmentCard(segment, segment.id == selectedId) {
                            onSelect(segment.id)
                            listRequested = false
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SelectedCaptionEditor(
    segment: CaptionSegment,
    canMergeNext: Boolean,
    translationAvailable: Boolean,
    demoMode: Boolean,
    onSourceChange: (String) -> Unit,
    onTranslationChange: (String) -> Unit,
    onRetranslate: () -> Unit,
    onSplit: () -> Unit,
    onMergeNext: () -> Unit,
) {
    var translationExpanded by rememberSaveable(segment.id) { mutableStateOf(false) }
    Surface(color = SubLokaColors.Surface, shape = RoundedCornerShape(12.dp)) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("${segment.sourceLanguage.label.uppercase()} · ASLI", style = MaterialTheme.typography.labelMedium)
            OutlinedTextField(
                label = { Text("Teks asli") },
                value = segment.sourceText,
                onValueChange = onSourceChange,
                modifier = Modifier.fillMaxWidth(),
                minLines = 2,
                maxLines = 4,
            )
            TextButton(onClick = { translationExpanded = !translationExpanded }, modifier = Modifier.fillMaxWidth()) {
                Text("${if (translationExpanded) "Sembunyikan" else "Buka"} terjemahan · ${segment.sourceLanguage.target.label}")
            }
            Text(translationLabel(segment.translationStatus), color = translationColor(segment.translationStatus),
                style = MaterialTheme.typography.labelMedium)
            if (translationExpanded) {
                if (segment.translationStatus == TranslationStatus.STALE) {
                    Text("Perlu diperbarui", color = SubLokaColors.Warning, style = MaterialTheme.typography.labelMedium)
                }
                OutlinedTextField(
                    label = { Text("Terjemahan") },
                    value = segment.translationText,
                    onValueChange = onTranslationChange,
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 2,
                    maxLines = 4,
                )
                if (segment.translationStatus != TranslationStatus.CURRENT) {
                    SecondaryAction(if (demoMode) "Terjemahan tidak tersedia pada contoh" else "Terjemahkan caption ini",
                        onRetranslate, enabled = translationAvailable, modifier = Modifier.fillMaxWidth())
                    if (!demoMode && segment.translationOrigin == app.subloka.core.domain.TranslationOrigin.MANUAL) {
                        Text("Terjemahan manual dilindungi. Koreksi langsung pada kolom terjemahan.", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(formatTime(segment.startUs), color = SubLokaColors.TextSecondary)
                Text(formatTime(segment.endUs), color = SubLokaColors.TextSecondary)
            }
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                SecondaryAction("Pecah di tengah", onClick = onSplit, enabled = segment.endUs - segment.startUs > 1L, modifier = Modifier.weight(1f))
                SecondaryAction("Gabung berikutnya", onClick = onMergeNext, enabled = canMergeNext, modifier = Modifier.weight(1f))
            }
            if (!canMergeNext) Text("Caption terakhir; tidak ada caption berikutnya untuk digabung.",
                style = MaterialTheme.typography.bodySmall, color = SubLokaColors.TextSecondary)
        }
    }
}

@Composable
private fun SegmentCard(segment: CaptionSegment, selected: Boolean, onClick: () -> Unit) {
    Surface(
        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).semantics { this.selected = selected }.clickable(onClick = onClick),
        color = if (selected) SubLokaColors.Primary.copy(alpha = 0.12f) else SubLokaColors.Surface,
        shape = RoundedCornerShape(10.dp),
    ) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text("${formatTime(segment.startUs)} – ${formatTime(segment.endUs)}", color = SubLokaColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
            Text("${segment.sourceLanguage.code} · ASLI", style = MaterialTheme.typography.labelSmall)
            Text(segment.sourceText, maxLines = 2, overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis)
            Text("${segment.sourceLanguage.target.code} · TERJEMAHAN", style = MaterialTheme.typography.labelSmall)
            Text(segment.translationText, maxLines = 2, overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis, color = SubLokaColors.TextSecondary)
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
