package app.subloka

import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import app.subloka.core.domain.ProjectSummary
import app.subloka.demo.DemoData
import app.subloka.feature.editor.EditorScreen
import app.subloka.feature.export.ExportScreen
import app.subloka.feature.projects.*

@Composable
fun SubLokaApp(
    modifier: Modifier = Modifier,
    persistence: SubLokaViewModel = viewModel(),
    media: SubLokaMediaViewModel = viewModel(),
) {
    var route by rememberSaveable { mutableStateOf("projects") }
    val segments by persistence.segments.collectAsState()
    val style by persistence.style.collectAsState()
    val saveState by persistence.saveState.collectAsState()
    val project by persistence.project.collectAsState()
    val projects by persistence.projects.collectAsState()
    val asr by persistence.asr.collectAsState()
    val selection by media.selection.collectAsState()
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) media.select(uri)
    }
    val modelPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) persistence.prepareModel(uri)
    }
    // After process death there is no active job; reopen the persisted project from the list.
    LaunchedEffect(project, route) {
        if (project == null && route !in listOf("projects", "new")) route = "projects"
    }
    fun back() {
        if (asr.busy) persistence.cancelOperation()
        else persistence.flush { success -> if (success) route = "projects" }
    }
    BackHandler(route != "projects") { back() }
    when (route) {
        "projects" -> ProjectsScreen(
            projects = projects.map { p -> ProjectSummary(p.id, p.title, p.sourceDisplayName, p.sourceLanguage,
                "%02d:%02d".format(p.durationUs / 60_000_000, p.durationUs / 1_000_000 % 60),
                "${p.widthPx} × ${p.heightPx}", "Tersimpan lokal") },
            onNewProject = { media.clear(); route = "new" },
            onOpenProject = { p -> persistence.openProject(p.id) { route = "editor" } }, modifier = modifier,
        )
        "new" -> NewProjectScreen(
            selectedMedia = (selection as? MediaSelectionState.Ready)?.descriptor,
            mediaLoading = selection == MediaSelectionState.Loading || saveState == PersistenceSaveState.SAVING,
            mediaError = (selection as? MediaSelectionState.Error)?.message
                ?: if (saveState == PersistenceSaveState.FAILED) "Proyek gagal disimpan. Coba lagi." else null,
            onPickVideo = { picker.launch(arrayOf("video/*")) }, onBack = ::back,
            onContinue = { language ->
                (selection as? MediaSelectionState.Ready)?.descriptor?.let { descriptor ->
                    persistence.persistMediaSelection(descriptor, language) { ok -> if (ok) route = "model" }
                }
            }, modifier = modifier,
        )
        "model" -> ModelSetupScreen(asr.modelReady, asr.busy, asr.stage, asr.error,
            onImport = { modelPicker.launch(arrayOf("*/*")) }, onDownload = { persistence.prepareModel() },
            onReady = { persistence.startTranscription(); route = "processing" },
            onBack = ::back, onCancel = persistence::cancelOperation, modifier = modifier)
        "processing" -> ProcessingScreen(asr.busy, asr.stage, asr.error, asr.completed,
            onCancel = persistence::cancelOperation, onRetry = { route = "model" },
            onOpenEditor = { route = "editor" }, onBack = ::back, modifier = modifier)
        "editor" -> project?.let { p ->
            key(p.id) {
                EditorScreen(initialSegments = segments, initialStyle = style,
                    mediaUri = p.sourceUri.takeUnless { it.startsWith("demo://") },
                    projectTitle = p.title, demoMode = p.id == DemoData.PROJECT_ID || p.sourceUri.startsWith("demo://"), durationUs = p.durationUs,
                    onGenerate = { route = "model" },
                    saveStatusText = saveState.label(), saveFailed = saveState == PersistenceSaveState.FAILED,
                    onSegmentsPersist = persistence::persistSegments, onStylePersist = persistence::persistStyle,
                    onBack = ::back, onExport = { route = "export" }, modifier = modifier)
            }
        }
        "export" -> ExportScreen(segments = segments, onBack = { route = "editor" }, onDone = ::back, modifier = modifier)
    }
}

private fun PersistenceSaveState.label(): String = when (this) {
    PersistenceSaveState.LOADING -> "Menyiapkan penyimpanan…"
    PersistenceSaveState.SAVING -> "Menyimpan…"
    PersistenceSaveState.SAVED -> "✓ Tersimpan lokal"
    PersistenceSaveState.FAILED -> "! Gagal menyimpan"
}
