package app.subloka

import android.Manifest
import android.os.Build
import android.content.pm.PackageManager
import androidx.compose.ui.platform.LocalContext
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import app.subloka.core.domain.TranslationEligibility
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
    exporter: SrtExportViewModel = viewModel(),
    videoExporter: VideoExportViewModel = viewModel(),
) {
    var route by rememberSaveable { mutableStateOf("projects") }
    val segments by persistence.segments.collectAsState()
    val style by persistence.style.collectAsState()
    val saveState by persistence.saveState.collectAsState()
    val project by persistence.project.collectAsState()
    val projects by persistence.projects.collectAsState()
    val homeAsrSession by AsrSession.state.collectAsState()
    val homeRenderSession by RenderSession.state.collectAsState()
    val relink by persistence.sourceRelink.collectAsState()
    val lifecycleOwner = androidx.lifecycle.compose.LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner, project?.id) {
        val observer = androidx.lifecycle.LifecycleEventObserver { _, event ->
            if (event == androidx.lifecycle.Lifecycle.Event.ON_RESUME) persistence.checkSource()
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }
    var relinkProjectId by rememberSaveable { mutableStateOf<String?>(null) }
    val relinkPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        val id = relinkProjectId
        relinkProjectId = null
        if (uri != null && id != null) persistence.relinkSource(id, uri) { route = "editor" }
    }
    val asr by persistence.asr.collectAsState()
    val context = LocalContext.current
    val notificationPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { _ ->
        // Notification permission is optional for starting a foreground service.
        persistence.startTranscription()
        route = "processing"
    }
    LaunchedEffect(asr.serviceJobId) {
        if (asr.serviceJobId != null) route = "processing"
    }
    val translation by persistence.translation.collectAsState()
    val translationSession by TranslationSession.state.collectAsState()
    LaunchedEffect(translation.serviceJobId) {
        if (translation.serviceJobId != null) route = "translation"
    }
    var pendingTranslationResume by rememberSaveable { mutableStateOf(false) }
    var pendingTranslationReplace by rememberSaveable { mutableStateOf(false) }
    var translationTarget by rememberSaveable { mutableStateOf<String?>(null) }
    val translationNotificationPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { _ ->
        if (pendingTranslationResume) persistence.resumeTranslation()
        else persistence.startTranslation(translationTarget, pendingTranslationReplace)
    }
    fun beginTranslation(resume: Boolean, replace: Boolean = false) {
        pendingTranslationResume = resume
        pendingTranslationReplace = replace
        if (Build.VERSION.SDK_INT >= 33 && context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            translationNotificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        } else if (resume) persistence.resumeTranslation()
        else persistence.startTranslation(translationTarget, replace)
    }
    val videoExportState by videoExporter.state.collectAsState()
    LaunchedEffect(videoExportState.serviceJobId, project?.id) {
        if (videoExportState.serviceJobId != null && project?.id == RenderSession.state.value?.request?.project?.id) route = "export"
    }
    var pendingRender by remember { mutableStateOf<Triple<app.subloka.core.domain.CaptionProject,
        List<app.subloka.core.domain.CaptionSegment>, app.subloka.core.domain.CaptionStyle>?>(null) }
    val renderNotificationPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { _ ->
        pendingRender?.let { (p, captions, captionStyle) ->
            if (!asr.busy) videoExporter.render(p, captions, captionStyle)
        }
        pendingRender = null
    }
    val mp4Picker = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("video/mp4")) {
        videoExporter.save(it)
    }
    val exportState by exporter.state.collectAsState()
    val srtPicker = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/x-subrip")) {
        exporter.save(it)
    }
    val selection by media.selection.collectAsState()
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) media.select(uri)
    }
    var importVad by rememberSaveable { mutableStateOf(false) }
    val translationModelPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) persistence.importTranslationModel(uri)
    }
    val modelPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) persistence.prepareModel(uri, importVad)
    }
    // After process death there is no active job; reopen the persisted project from the list.
    LaunchedEffect(project, route) {
        if (project == null && route !in listOf("projects", "new")) route = "projects"
    }
    fun back() {
        if (route == "relink" && relink.busy) return
        if (route == "export" && videoExportState.rendering) { videoExporter.cancelRender(); return }
        if (route == "export" && (exportState.busy || exportState.pending != null || videoExportState.busy || videoExportState.pending)) return
        if (asr.busy) persistence.cancelOperation()
        else persistence.flush { success -> if (success) route = if (route in listOf("translation", "export", "relink")) "editor" else "projects" }
    }
    BackHandler(route != "projects") { back() }
    when (route) {
        "projects" -> ProjectsScreen(
            projects = projects.map { p -> ProjectSummary(p.id, p.title, p.sourceDisplayName, p.sourceLanguage,
                "%02d:%02d".format(p.durationUs / 60_000_000, p.durationUs / 1_000_000 % 60),
                "${p.widthPx} × ${p.heightPx}",
                "Diperbarui " + java.text.DateFormat.getDateTimeInstance(java.text.DateFormat.SHORT, java.text.DateFormat.SHORT)
                    .format(java.util.Date(p.updatedAtMs)),
                statusLabel = when {
                    homeAsrSession?.let { it.running && it.request.project.id == p.id } == true ->
                        if (homeAsrSession?.stopping == true) "Menghentikan transkripsi…" else "Transkripsi berjalan"
                    translationSession?.let { it.running && it.request.project.id == p.id } == true ->
                        if (translationSession?.stopping == true) "Menghentikan terjemahan…" else "Terjemahan berjalan"
                    homeRenderSession?.let { it.running && it.request.project.id == p.id } == true ->
                        if (homeRenderSession?.stopping == true) "Menghentikan render…" else "Render berjalan"
                    else -> "Tersimpan di perangkat"
                }) },
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
            useTurbo = asr.useTurbo, onModelSelected = persistence::selectCaptionModel,
            onImport = { importVad = false; modelPicker.launch(arrayOf("*/*")) },
            onImportVad = { importVad = true; modelPicker.launch(arrayOf("*/*")) }, onDownload = { persistence.prepareModel() },
            onReady = {
                if (Build.VERSION.SDK_INT >= 33 && context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                    notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
                } else { persistence.startTranscription(); route = "processing" }
            },
            onBack = ::back, onCancel = persistence::cancelOperation, modifier = modifier)
        "processing" -> ProcessingScreen(asr.busy, asr.stage, asr.error, asr.completed,
            onCancel = persistence::cancelOperation, onRetry = { route = "model" },
            onOpenEditor = { route = "editor" }, onBack = ::back, modifier = modifier,
            stopping = homeAsrSession?.stopping == true)
        "translation" -> project?.let { p ->
            TranslationSetupScreen(translation.ready, asr.busy, translation.stage, translation.error,
                recoveryCount = translation.pendingCount, hasRecovery = translation.pendingId != null,
                backgroundRunning = translationSession?.running == true,
                stopping = translationSession?.stopping == true,
                onResume = { beginTranslation(true) }, onDiscardRecovery = persistence::discardTranslationRecovery,
                eligibleCount = segments.count { (translationTarget == null || it.id == translationTarget) && TranslationEligibility.canGenerate(it) },
                replaceableCount = segments.count { (translationTarget == null || it.id == translationTarget) && TranslationEligibility.canGenerate(it, true) },
                useGemma = translation.useGemma, termsAccepted = translation.termsAccepted,
                onModelSelected = persistence::selectTranslationModel, onTermsAccepted = persistence::acceptGemmaTerms,
                onImport = { translationModelPicker.launch(arrayOf("*/*")) },
                pairLabel = "${p.sourceLanguage.label} → ${p.targetLanguage.label}",
                onCheck = persistence::checkTranslationModel,
                onDownload = persistence::prepareTranslationModel,
                onTranslate = { replace -> beginTranslation(false, replace) },
                onCancel = persistence::cancelOperation, onBack = ::back, modifier = modifier)
        }
        "editor" -> project?.let { p ->
            key(p.id, p.sourceUri, relink.epoch) {
                EditorScreen(initialSegments = segments, initialStyle = style,
                    sourceUnavailable = relink.unavailable,
                    onVideoError = persistence::sourcePlaybackFailed,
                    onRelink = {
                        persistence.flush { success -> if (success && !asr.busy) route = "relink" }
                    },
                    mediaUri = p.sourceUri.takeUnless { it.startsWith("demo://") },
                    projectTitle = if (p.sourceUri.startsWith("demo://")) "${p.title} · contoh" else p.title, demoMode = p.id == DemoData.PROJECT_ID || p.sourceUri.startsWith("demo://"), durationUs = p.durationUs,
                    videoWidth = if (p.rotationDegrees in setOf(90, 270)) p.heightPx else p.widthPx,
                    videoHeight = if (p.rotationDegrees in setOf(90, 270)) p.widthPx else p.heightPx,
                    onGenerate = { route = "model" },
                    onRequestTranslation = { segmentId ->
                        persistence.flush { success ->
                            if (success && !asr.busy) {
                                translationTarget = segmentId
                                route = "translation"
                                persistence.checkTranslationModel()
                            }
                        }
                    },
                    saveStatusText = saveState.label(), saveFailed = saveState == PersistenceSaveState.FAILED,
                    onRetrySave = persistence::retryEditorSave,
                    onSegmentsPersist = persistence::persistSegments, onStylePersist = persistence::persistStyle,
                    onBack = ::back, onExport = { snapshot ->
                        persistence.persistSegments(snapshot)
                        persistence.flush { success ->
                            if (success && !asr.busy) { exporter.reset(); videoExporter.reset(); route = "export" }
                        }
                    }, modifier = modifier)
            }
        }
        "relink" -> project?.let { p ->
            RelinkVideoScreen(p.sourceDisplayName, relink.busy, relink.message,
                onPick = {
                    relinkProjectId = p.id
                    try { relinkPicker.launch(arrayOf("video/*")) }
                    catch (_: Exception) { relinkProjectId = null; persistence.relinkPickerFailed() }
                }, onBack = ::back, modifier = modifier)
        }
        "export" -> project?.let { p ->
            ExportScreen(segments, p.sourceLanguage,
                p.id == DemoData.PROJECT_ID || p.sourceUri.startsWith("demo://"),
                exportState.busy || videoExportState.busy, exportState.pending != null || videoExportState.pending, exportState.documents,
                exportState.saved, exportState.message,
                onPrepare = { mode -> exporter.prepare(p.title, p.sourceLanguage, p.durationUs, segments, mode) },
                onSave = { index -> exporter.select(index)?.let { name ->
                    try { srtPicker.launch(name) } catch (_: Exception) { exporter.pickerFailed() }
                } },
                videoReady = videoExportState.ready, videoRendering = videoExportState.rendering,
                videoMessage = videoExportState.message, videoProgress = videoExportState.progress,
                onRender = { mode ->
                    if (!asr.busy && !exportState.busy && exportState.pending == null) {
                        val renderStyle = style.copy(displayMode = when (mode) {
                            app.subloka.core.domain.SrtExportMode.SOURCE -> app.subloka.core.domain.CaptionDisplayMode.ORIGINAL
                            app.subloka.core.domain.SrtExportMode.TRANSLATION -> app.subloka.core.domain.CaptionDisplayMode.TRANSLATION
                            app.subloka.core.domain.SrtExportMode.BOTH -> app.subloka.core.domain.CaptionDisplayMode.DUAL
                        })
                        if (Build.VERSION.SDK_INT >= 33 && context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                            pendingRender = Triple(p, segments.toList(), renderStyle)
                            renderNotificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
                        } else videoExporter.render(p, segments, renderStyle)
                    }
                },
                onSaveVideo = { videoExporter.select()?.let { name ->
                    try { mp4Picker.launch(name) } catch (_: Exception) { videoExporter.pickerFailed() }
                } }, onCancelVideo = videoExporter::cancelRender,
                onBack = ::back, modifier = modifier)
        }
    }
}

private fun PersistenceSaveState.label(): String = when (this) {
    PersistenceSaveState.LOADING -> "Menyiapkan penyimpanan…"
    PersistenceSaveState.SAVING -> "Menyimpan…"
    PersistenceSaveState.SAVED -> "✓ Tersimpan lokal"
    PersistenceSaveState.FAILED -> "Perubahan belum tersimpan"
}
