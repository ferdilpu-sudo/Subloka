package app.subloka.feature.editor

import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.TextButton
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Tab
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
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
import app.subloka.core.domain.TranslationEligibility
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
    projectTitle: String = "Traveling",
    demoMode: Boolean = true,
    durationUs: Long = initialSegments.maxOfOrNull { it.endUs } ?: 1L,
    videoWidth: Int = 16,
    videoHeight: Int = 9,
    sourceUnavailable: Boolean = false,
    onRelink: () -> Unit = {},
    onVideoError: () -> Unit = {},
    onGenerate: () -> Unit = {},
    onRequestTranslation: (String?) -> Unit = {},
    onRetrySave: ((List<CaptionSegment>, CaptionStyle) -> Unit)? = null,
) {
    if (initialSegments.isEmpty()) {
        Column(modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text(projectTitle, style = MaterialTheme.typography.headlineSmall)
            if (!demoMode) {
                if (sourceUnavailable) Text("Video sumber tidak dapat diakses. Caption tetap tersimpan.")
                app.subloka.core.designsystem.SecondaryAction("Tautkan ulang video", onRelink)
            }
            Text("Belum ada caption. Audio hening juga dapat menghasilkan daftar kosong.")
            app.subloka.core.designsystem.PrimaryAction("Buat caption", onGenerate)
            app.subloka.core.designsystem.SecondaryAction("Kembali", onBack)
        }
        return
    }
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

    var previewRequested by remember { mutableStateOf(true) }
    BoxWithConstraints(modifier = modifier.fillMaxSize()) {
        // Short landscape phones still need video context; height must not force
        // them into the portrait path that intentionally hides the preview.
        val expanded = maxWidth >= 600.dp && (maxWidth > maxHeight || maxWidth >= 840.dp)
        val compactLandscapePreview = maxHeight < 480.dp
        val density = LocalDensity.current
        val keyboardLikelyVisible = WindowInsets.ime.getBottom(density) > 0
        val hasPreviewSpace = maxHeight >= if (keyboardLikelyVisible) 560.dp else 600.dp
        val showPreview = previewRequested && hasPreviewSpace
        val selected = segments.first { it.id == selectedId }

        Column(modifier = Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            ProjectTopBar(
                onBack = onBack,
                onExport = { onExport(segments) },
                saveStatusText = saveStatusText,
                saveFailed = saveFailed,
                title = projectTitle,
                exportAvailable = !saveFailed,
                onRetrySave = onRetrySave?.let { retry -> { retry(segments, style) } },
            )
            if (!demoMode && sourceUnavailable) {
                Text("Video tidak dapat dibuka. Tautkan file asli untuk memulihkan pemutaran.",
                    style = MaterialTheme.typography.bodySmall)
            }
            if (!demoMode && sourceUnavailable) {
                androidx.compose.material3.TextButton(onClick = onRelink) { Text("Tautkan ulang video") }
            }
            if (hasPreviewSpace && !keyboardLikelyVisible) {
                if (demoMode) DemoBadge() else Text("Prototipe • periksa teks, waktu, dan makna terjemahan sebelum ekspor.", style = MaterialTheme.typography.bodySmall)
            }

            if (!demoMode && !keyboardLikelyVisible && !expanded) {
                val count = segments.count(TranslationEligibility::canGenerate)
                app.subloka.core.designsystem.SecondaryAction(if (count > 0) "Terjemahkan / perbarui $count caption" else "Model / lanjutkan terjemahan",
                    { onRequestTranslation(null) }, enabled = segments.isNotEmpty(), modifier = Modifier.fillMaxWidth())
            }

            if (expanded) {
                Row(
                    modifier = Modifier.weight(1f),
                    horizontalArrangement = Arrangement.spacedBy(18.dp),
                ) {
                    Column(modifier = Modifier.weight(0.95f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        VideoPreview(onVideoError = onVideoError, segment = selected, segments = segments, mediaUri = mediaUri, captionStyle = style, videoWidth = videoWidth, videoHeight = videoHeight, compactHeight = compactLandscapePreview)
                        if (!demoMode && !keyboardLikelyVisible) {
                            val count = segments.count(TranslationEligibility::canGenerate)
                            app.subloka.core.designsystem.SecondaryAction(
                                if (count > 0) "Terjemahkan / perbarui $count caption" else "Model / lanjutkan terjemahan",
                                { onRequestTranslation(null) }, enabled = segments.isNotEmpty(),
                                modifier = Modifier.fillMaxWidth())
                        }
                        WorkspaceSwitcher(workspace = workspace, onWorkspaceChange = { workspace = it })
                    }
                    WorkspacePanel(
                        demoMode = demoMode, durationUs = durationUs, onRequestTranslation = onRequestTranslation,
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
                if (hasPreviewSpace && !keyboardLikelyVisible) {
                    TextButton(onClick = { previewRequested = !previewRequested }) {
                        Text(if (previewRequested) "Sembunyikan pratinjau" else "Tampilkan pratinjau")
                    }
                }
                if (showPreview) VideoPreview(onVideoError = onVideoError, segment = selected, segments = segments, mediaUri = mediaUri, captionStyle = style, videoWidth = videoWidth, videoHeight = videoHeight, compactHeight = true)
                WorkspaceSwitcher(workspace = workspace, onWorkspaceChange = { workspace = it })
                WorkspacePanel(
                    demoMode = demoMode, durationUs = durationUs, onRequestTranslation = onRequestTranslation,
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
    title: String,
    exportAvailable: Boolean,
    onRetrySave: (() -> Unit)?,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        TextButton(onClick = onBack, modifier = Modifier.semantics { contentDescription = "Kembali" }) {
            Text("‹", style = MaterialTheme.typography.headlineSmall)
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(title, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.titleMedium)
            Text(saveStatusText, maxLines = 2, overflow = TextOverflow.Ellipsis,
                color = if (saveFailed) SubLokaColors.Error else SubLokaColors.TextSecondary,
                style = MaterialTheme.typography.labelSmall)
            if (saveFailed && onRetrySave != null) {
                TextButton(onClick = onRetrySave) { Text("Coba simpan lagi") }
            }
        }
        FilledTonalButton(onClick = onExport, enabled = exportAvailable) { Text("Ekspor") }
    }
}

@Composable
private fun WorkspaceSwitcher(workspace: EditorWorkspace, onWorkspaceChange: (EditorWorkspace) -> Unit) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
        EditorWorkspace.entries.forEach { item ->
            Tab(selected = workspace == item, onClick = { onWorkspaceChange(item) },
                modifier = Modifier.weight(1f),
                text = { Text(when (item) {
                    EditorWorkspace.CAPTION -> "Teks"
                    EditorWorkspace.TIMING -> "Waktu"
                    EditorWorkspace.STYLE -> "Gaya"
                }) })
        }
    }
}

@Composable
private fun WorkspacePanel(
    onRequestTranslation: (String?) -> Unit,
    demoMode: Boolean,
    durationUs: Long,
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
            demoMode = demoMode,
            translationAvailable = demoMode || TranslationEligibility.canGenerate(selected, true),
            onRetranslate = {
                if (!demoMode) onRequestTranslation(selected.id) else onSegmentsChange(
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
        EditorWorkspace.TIMING -> TimingWorkspace(segment = selected,
            navigation = { CaptionNavigation(segments, selectedId, onSelect) },
            minimumStartUs = segments.getOrNull(selectedIndex - 1)?.endUs ?: 0L,
            maximumEndUs = segments.getOrNull(selectedIndex + 1)?.startUs ?: durationUs,
            onChange = { start, end ->
                onSegmentsChange(segments.toMutableList().also { it[selectedIndex] = selected.copy(startUs = start, endUs = end) })
            }, modifier = modifier)
        EditorWorkspace.STYLE -> StyleWorkspace(style = style, onStyleChange = onStyleChange, modifier = modifier)
    }
}

private fun demoRetranslation(source: String, sourceCode: String): String =
    if (sourceCode == "EN") "[Demo ID] $source" else "[Demo EN] $source"
