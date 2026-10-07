package app.subloka.feature.editor

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.DemoBadge
import app.subloka.core.designsystem.SubLokaColors
import app.subloka.core.domain.CaptionEditingRules
import app.subloka.core.domain.CaptionSegment
import app.subloka.core.domain.CaptionStyle
import app.subloka.core.domain.EditorWorkspace
import app.subloka.core.domain.TranslationOrigin
import app.subloka.core.domain.TranslationStatus
import java.util.UUID

@Composable
fun EditorScreen(
    initialSegments: List<CaptionSegment>,
    initialStyle: CaptionStyle,
    mediaUri: String?,
    saveStatusText: String,
    saveFailed: Boolean,
    onSegmentsPersist: (List<CaptionSegment>) -> Unit,
    onStylePersist: (CaptionStyle) -> Unit,
    onBack: () -> Unit,
    onExport: (List<CaptionSegment>) -> Unit,
    modifier: Modifier = Modifier,
) {
    var segments by remember { mutableStateOf(initialSegments) }
    var selectedId by remember { mutableStateOf(initialSegments.first().id) }
    var workspace by remember { mutableStateOf(EditorWorkspace.CAPTION) }
    var style by remember { mutableStateOf(initialStyle) }

    fun commitSegments(next: List<CaptionSegment>, nextSelectedId: String? = null) {
        segments = next.sortedBy { it.startUs }
        if (nextSelectedId != null) selectedId = nextSelectedId
        onSegmentsPersist(segments)
    }

    fun splitSelected() {
        val index = segments.indexOfFirst { it.id == selectedId }
        if (index < 0) return
        val selected = segments[index]
        val splitUs = selected.startUs + ((selected.endUs - selected.startUs) / 2)
        if (splitUs <= selected.startUs || splitUs >= selected.endUs) return

        val ratio = (splitUs - selected.startUs).toDouble() / (selected.endUs - selected.startUs).toDouble()
        val sourceParts = CaptionEditingRules.splitTextSuggestion(selected.sourceText, ratio)
        val translationParts = CaptionEditingRules.splitTextSuggestion(selected.translationText, ratio)
        val hasTranslation = selected.translationText.isNotBlank()
        val status = if (hasTranslation) TranslationStatus.STALE else TranslationStatus.MISSING
        val origin = if (hasTranslation) selected.translationOrigin else TranslationOrigin.NONE

        val left = selected.copy(
            id = UUID.randomUUID().toString(),
            endUs = splitUs,
            sourceText = sourceParts.first,
            translationText = translationParts.first,
            translationStatus = status,
            translationOrigin = origin,
            sourceRevision = 1,
            translationSourceRevision = if (hasTranslation) 0 else null,
        )
        val right = selected.copy(
            id = UUID.randomUUID().toString(),
            startUs = splitUs,
            sourceText = sourceParts.second,
            translationText = translationParts.second,
            translationStatus = status,
            translationOrigin = origin,
            sourceRevision = 1,
            translationSourceRevision = if (hasTranslation) 0 else null,
        )

        val next = segments.toMutableList().apply {
            removeAt(index)
            add(index, right)
            add(index, left)
        }
        commitSegments(next, left.id)
    }

    fun mergeSelectedWithNext() {
        val ordered = segments.sortedBy { it.startUs }
        val index = ordered.indexOfFirst { it.id == selectedId }
        if (index < 0 || index >= ordered.lastIndex) return

        val first = ordered[index]
        val second = ordered[index + 1]
        val mergedTranslation = CaptionEditingRules.mergeText(first.translationText, second.translationText)
        val hasTranslation = mergedTranslation.isNotBlank()
        val origin = when {
            !hasTranslation -> TranslationOrigin.NONE
            first.translationOrigin == TranslationOrigin.MANUAL ||
                second.translationOrigin == TranslationOrigin.MANUAL -> TranslationOrigin.MANUAL
            else -> TranslationOrigin.MACHINE
        }
        val merged = first.copy(
            id = UUID.randomUUID().toString(),
            endUs = second.endUs,
            sourceText = CaptionEditingRules.mergeText(first.sourceText, second.sourceText),
            translationText = mergedTranslation,
            translationStatus = if (hasTranslation) TranslationStatus.STALE else TranslationStatus.MISSING,
            translationOrigin = origin,
            sourceRevision = 1,
            translationSourceRevision = if (hasTranslation) 0 else null,
        )

        val next = ordered.toMutableList().apply {
            removeAt(index + 1)
            removeAt(index)
            add(index, merged)
        }
        commitSegments(next, merged.id)
    }

    BoxWithConstraints(modifier = modifier.fillMaxSize()) {
        val expanded = maxWidth >= 840.dp
        val density = LocalDensity.current
        val keyboardLikelyVisible = WindowInsets.ime.getBottom(density) > 0
        val selected = segments.first { it.id == selectedId }

        Column(modifier = Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            ProjectTopBar(
                onBack = onBack,
                onExport = { onExport(segments) },
                saveStatusText = saveStatusText,
                saveFailed = saveFailed,
            )
            DemoBadge()

            if (expanded) {
                Row(
                    modifier = Modifier.fillMaxSize(),
                    horizontalArrangement = Arrangement.spacedBy(18.dp),
                ) {
                    Column(modifier = Modifier.weight(0.95f), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        VideoPreview(segment = selected, mediaUri = mediaUri, compactHeight = false)
                        WorkspaceSwitcher(workspace = workspace, onWorkspaceChange = { workspace = it })
                    }
                    WorkspacePanel(
                        workspace = workspace,
                        segments = segments,
                        selectedId = selectedId,
                        style = style,
                        onSelect = { selectedId = it },
                        onSegmentsChange = { commitSegments(it) },
                        onStyleChange = {
                            style = it
                            onStylePersist(it)
                        },
                        onSplit = ::splitSelected,
                        onMergeNext = ::mergeSelectedWithNext,
                        modifier = Modifier.weight(1.05f),
                    )
                }
            } else {
                VideoPreview(segment = selected, mediaUri = mediaUri, compactHeight = keyboardLikelyVisible)
                WorkspaceSwitcher(workspace = workspace, onWorkspaceChange = { workspace = it })
                WorkspacePanel(
                    workspace = workspace,
                    segments = segments,
                    selectedId = selectedId,
                    style = style,
                    onSelect = { selectedId = it },
                    onSegmentsChange = { commitSegments(it) },
                    onStyleChange = {
                        style = it
                        onStylePersist(it)
                    },
                    onSplit = ::splitSelected,
                    onMergeNext = ::mergeSelectedWithNext,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun ProjectTopBar(
    onBack: () -> Unit,
    onExport: () -> Unit,
    saveStatusText: String,
    saveFailed: Boolean,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("‹", modifier = Modifier.clickable(onClick = onBack), style = MaterialTheme.typography.headlineSmall)
            Column {
                Text("Traveling", style = MaterialTheme.typography.titleMedium)
                Text(
                    saveStatusText,
                    color = if (saveFailed) SubLokaColors.Error else SubLokaColors.TextSecondary,
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("↶", color = SubLokaColors.TextSecondary)
            Text("↷", color = SubLokaColors.TextSecondary)
            Text("Export", modifier = Modifier.clickable(onClick = onExport), color = SubLokaColors.Primary)
        }
    }
}

@Composable
private fun WorkspaceSwitcher(workspace: EditorWorkspace, onWorkspaceChange: (EditorWorkspace) -> Unit) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
        EditorWorkspace.entries.forEach { item ->
            Text(
                text = item.name.lowercase().replaceFirstChar { it.uppercase() },
                modifier = Modifier.clickable { onWorkspaceChange(item) }.padding(horizontal = 12.dp, vertical = 10.dp),
                color = if (workspace == item) SubLokaColors.Primary else SubLokaColors.TextSecondary,
                style = MaterialTheme.typography.labelLarge,
            )
        }
    }
}

@Composable
private fun WorkspacePanel(
    workspace: EditorWorkspace,
    segments: List<CaptionSegment>,
    selectedId: String,
    style: CaptionStyle,
    onSelect: (String) -> Unit,
    onSegmentsChange: (List<CaptionSegment>) -> Unit,
    onStyleChange: (CaptionStyle) -> Unit,
    onSplit: () -> Unit,
    onMergeNext: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val selectedIndex = segments.indexOfFirst { it.id == selectedId }
    val selected = segments[selectedIndex]

    when (workspace) {
        EditorWorkspace.CAPTION -> CaptionWorkspace(
            segments = segments,
            selectedId = selectedId,
            onSelect = onSelect,
            onSourceChange = { newText ->
                onSegmentsChange(
                    segments.toMutableList().also { list ->
                        list[selectedIndex] = selected.copy(
                            sourceText = newText,
                            sourceRevision = selected.sourceRevision + 1,
                            translationStatus = if (selected.translationText.isBlank()) {
                                TranslationStatus.MISSING
                            } else {
                                TranslationStatus.STALE
                            },
                        )
                    },
                )
            },
            onTranslationChange = { newText ->
                onSegmentsChange(
                    segments.toMutableList().also { list ->
                        list[selectedIndex] = selected.copy(
                            translationText = newText,
                            translationStatus = if (newText.isBlank()) TranslationStatus.MISSING else TranslationStatus.CURRENT,
                            translationOrigin = if (newText.isBlank()) TranslationOrigin.NONE else TranslationOrigin.MANUAL,
                            translationSourceRevision = if (newText.isBlank()) null else selected.sourceRevision,
                        )
                    },
                )
            },
            onRetranslate = {
                onSegmentsChange(
                    segments.toMutableList().also { list ->
                        list[selectedIndex] = selected.copy(
                            translationText = demoRetranslation(selected.sourceText, selected.sourceLanguage.code),
                            translationStatus = TranslationStatus.CURRENT,
                            translationOrigin = TranslationOrigin.MACHINE,
                            translationSourceRevision = selected.sourceRevision,
                        )
                    },
                )
            },
            onSplit = onSplit,
            onMergeNext = onMergeNext,
            modifier = modifier,
        )
        EditorWorkspace.TIMING -> TimingWorkspace(segment = selected, modifier = modifier)
        EditorWorkspace.STYLE -> StyleWorkspace(style = style, onStyleChange = onStyleChange, modifier = modifier)
    }
}

private fun demoRetranslation(source: String, sourceCode: String): String =
    if (sourceCode == "EN") "[Demo ID] $source" else "[Demo EN] $source"
