package app.subloka

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import app.subloka.core.domain.CaptionSegment
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
fun SubLokaApp(modifier: Modifier = Modifier) {
    var route by remember { mutableStateOf<DemoRoute>(DemoRoute.Projects) }
    var editorSegments by remember { mutableStateOf(DemoData.segments) }

    when (route) {
        DemoRoute.Projects -> ProjectsScreen(
            projects = listOf(DemoData.project),
            onNewProject = { route = DemoRoute.NewProject },
            onOpenProject = { route = DemoRoute.Editor },
            modifier = modifier,
        )
        DemoRoute.NewProject -> NewProjectScreen(
            onBack = { route = DemoRoute.Projects },
            onContinue = { route = DemoRoute.ModelSetup },
            modifier = modifier,
        )
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
            onBack = { route = DemoRoute.Projects },
            onExport = { segments ->
                editorSegments = segments
                route = DemoRoute.Export
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
