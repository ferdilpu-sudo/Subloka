package app.subloka

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import app.subloka.core.domain.CaptionStyle
import app.subloka.demo.DemoData
import app.subloka.feature.editor.EditorScreen
import app.subloka.feature.export.ExportScreen
import app.subloka.feature.projects.ModelSetupScreen
import app.subloka.feature.projects.NewProjectScreen
import app.subloka.feature.projects.ProcessingScreen
import app.subloka.feature.projects.ProjectsScreen

private sealed interface DemoRoute {
    data object Projects : DemoRoute
    data object NewProject : DemoRoute
    data object ModelSetup : DemoRoute
    data object Processing : DemoRoute
    data object Editor : DemoRoute
    data object Export : DemoRoute
}

@Composable
fun SubLokaApp(
    modifier: Modifier = Modifier,
    persistence: SubLokaViewModel = viewModel(),
    media: SubLokaMediaViewModel = viewModel(),
) {
    var route by remember { mutableStateOf<DemoRoute>(DemoRoute.Projects) }
    val persistedSegments by persistence.segments.collectAsState()
    val persistedStyle by persistence.style.collectAsState()
    val saveState by persistence.saveState.collectAsState()
    val sourceUri by persistence.sourceUri.collectAsState()
    val mediaSelection by media.selection.collectAsState()

    var editorSegments by remember { mutableStateOf(DemoData.segments) }
    var editorStyle by remember { mutableStateOf(CaptionStyle()) }

    val documentPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) media.select(uri)
    }

    LaunchedEffect(persistedSegments) {
        if (persistedSegments.isNotEmpty()) {
            editorSegments = persistedSegments
        }
    }
    LaunchedEffect(persistedStyle) {
        editorStyle = persistedStyle
    }

    when (route) {
        DemoRoute.Projects -> ProjectsScreen(
            projects = listOf(DemoData.project),
            onNewProject = {
                media.clear()
                route = DemoRoute.NewProject
            },
            onOpenProject = { route = DemoRoute.Editor },
            modifier = modifier,
        )
        DemoRoute.NewProject -> {
            val selected = (mediaSelection as? MediaSelectionState.Ready)?.descriptor
            NewProjectScreen(
                selectedMedia = selected,
                mediaLoading = mediaSelection == MediaSelectionState.Loading,
                mediaError = (mediaSelection as? MediaSelectionState.Error)?.message,
                onPickVideo = { documentPicker.launch(arrayOf("video/*")) },
                onBack = { route = DemoRoute.Projects },
                onContinue = { sourceLanguage ->
                    if (selected != null) {
                        persistence.persistMediaSelection(selected, sourceLanguage) { success ->
                            if (success) route = DemoRoute.ModelSetup
                        }
                    }
                },
                modifier = modifier,
            )
        }
        DemoRoute.ModelSetup -> ModelSetupScreen(
            onReady = { route = DemoRoute.Processing },
            modifier = modifier,
        )
        DemoRoute.Processing -> ProcessingScreen(
            stages = DemoData.stages,
            onCancel = { route = DemoRoute.Projects },
            onDemoComplete = { route = DemoRoute.Editor },
            modifier = modifier,
        )
        DemoRoute.Editor -> EditorScreen(
            initialSegments = editorSegments,
            initialStyle = editorStyle,
            mediaUri = sourceUri,
            saveStatusText = saveState.label(),
            saveFailed = saveState == PersistenceSaveState.FAILED,
            onSegmentsPersist = { segments ->
                editorSegments = segments
                persistence.persistSegments(segments)
            },
            onStylePersist = { style ->
                editorStyle = style
                persistence.persistStyle(style)
            },
            onBack = {
                persistence.flush { success ->
                    if (success) route = DemoRoute.Projects
                }
            },
            onExport = { segments ->
                editorSegments = segments
                persistence.persistSegments(segments)
                persistence.flush { success ->
                    if (success) route = DemoRoute.Export
                }
            },
            modifier = modifier,
        )
        DemoRoute.Export -> ExportScreen(
            segments = editorSegments,
            onBack = { route = DemoRoute.Editor },
            onDone = { route = DemoRoute.Projects },
            modifier = modifier,
        )
    }
}

private fun PersistenceSaveState.label(): String = when (this) {
    PersistenceSaveState.LOADING -> "Menyiapkan penyimpanan…"
    PersistenceSaveState.SAVING -> "Menyimpan…"
    PersistenceSaveState.SAVED -> "✓ Tersimpan lokal"
    PersistenceSaveState.FAILED -> "! Gagal menyimpan"
}
