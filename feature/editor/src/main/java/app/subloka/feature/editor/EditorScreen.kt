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
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.DemoBadge
import app.subloka.core.designsystem.SubLokaColors
import app.subloka.core.domain.CaptionSegment
import app.subloka.core.domain.CaptionStyle
import app.subloka.core.domain.EditorWorkspace
import app.subloka.core.domain.TranslationOrigin
import app.subloka.core.domain.TranslationStatus

@Composable
fun EditorScreen(
    initialSegments: List<CaptionSegment>,
    onBack: () -> Unit,
    onExport: (List<CaptionSegment>) -> Unit,
    modifier: Modifier = Modifier,
) {
    var segments by remember { mutableStateOf(initialSegments) }
    var selectedId by remember { mutableLongStateOf(initialSegments.first().id) }
    var workspace by remember { mutableStateOf(EditorWorkspace.CAPTION) }
    var style by remember { mutableStateOf(CaptionStyle()) }

    BoxWithConstraints(modifier = modifier.fillMaxSize()) {
        val expanded = maxWidth >= 840.dp
        val density = LocalDensity.current
        val keyboardLikelyVisible = WindowInsets.ime.getBottom(density) > 0
        val selected = segments.first { it.id == selectedId }

        Column(modifier = Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            ProjectTopBar(onBack = onBack, onExport = { onExport(segments) })
            DemoBadge()

            if (expanded) {
                Row(
                    modifier = Modifier.fillMaxSize(),
                    horizontalArrangement = Arrangement.spacedBy(18.dp),
                ) {
                    Column(modifier = Modifier.weight(0.95f), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        VideoPreview(segment = selected, compactHeight = false)
                        WorkspaceSwitcher(workspace = workspace, onWorkspaceChange = { workspace = it })
                    }
                    WorkspacePanel(
                        workspace = workspace,
                        segments = segments,
                        selectedId = selectedId,
                        style = style,
                        onSelect = { selectedId = it },
                        onSegmentsChange = { segments = it },
                        onStyleChange = { style = it },
                        modifier = Modifier.weight(1.05f),
                    )
                }
            } else {
                VideoPreview(segment = selected, compactHeight = keyboardLikelyVisible)
                WorkspaceSwitcher(workspace = workspace, onWorkspaceChange = { workspace = it })
                WorkspacePanel(
                    workspace = workspace,
                    segments = segments,
                    selectedId = selectedId,
                    style = style,
                    onSelect = { selectedId = it },
                    onSegmentsChange = { segments = it },
                    onStyleChange = { style = it },
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun ProjectTopBar(onBack: () -> Unit, onExport: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("‹", modifier = Modifier.clickable(onClick = onBack), style = MaterialTheme.typography.headlineSmall)
            Column {
                Text("Traveling", style = MaterialTheme.typography.titleMedium)
                Text("✓ Tersimpan", color = SubLokaColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
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
    selectedId: Long,
    style: CaptionStyle,
    onSelect: (Long) -> Unit,
    onSegmentsChange: (List<CaptionSegment>) -> Unit,
    onStyleChange: (CaptionStyle) -> Unit,
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
                            translationStatus = TranslationStatus.STALE,
                        )
                    },
                )
            },
            onTranslationChange = { newText ->
                onSegmentsChange(
                    segments.toMutableList().also { list ->
                        list[selectedIndex] = selected.copy(
                            translationText = newText,
                            translationStatus = TranslationStatus.CURRENT,
                            translationOrigin = TranslationOrigin.MANUAL,
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
                        )
                    },
                )
            },
            modifier = modifier,
        )
        EditorWorkspace.TIMING -> TimingWorkspace(segment = selected, modifier = modifier)
        EditorWorkspace.STYLE -> StyleWorkspace(style = style, onStyleChange = onStyleChange, modifier = modifier)
    }
}

private fun demoRetranslation(source: String, sourceCode: String): String =
    if (sourceCode == "EN") "[Demo ID] $source" else "[Demo EN] $source"
