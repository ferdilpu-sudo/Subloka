package app.subloka.feature.projects

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.PrimaryAction
import app.subloka.core.designsystem.SubLokaColors
import app.subloka.core.domain.ProjectSummary

@Composable
fun ProjectsScreen(
    projects: List<ProjectSummary>,
    onNewProject: () -> Unit,
    onOpenProject: (ProjectSummary) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column {
                Text("SubLoka", style = MaterialTheme.typography.headlineMedium)
                Text(
                    "Caption bilingual offline",
                    color = SubLokaColors.TextSecondary,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            Text("Settings", color = SubLokaColors.Primary)
        }

        PrimaryAction(
            text = "New Project",
            onClick = onNewProject,
            modifier = Modifier.fillMaxWidth(),
        )

        if (projects.isEmpty()) {
            Spacer(Modifier.height(28.dp))
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Belum ada project", style = MaterialTheme.typography.titleLarge)
                Text(
                    "Pilih video untuk membuat caption bilingual secara offline.",
                    color = SubLokaColors.TextSecondary,
                )
            }
        } else {
            Text("Recent projects", style = MaterialTheme.typography.titleMedium)
            projects.forEach { project ->
                ProjectCard(project = project, onClick = { onOpenProject(project) })
            }
        }
    }
}

@Composable
private fun ProjectCard(project: ProjectSummary, onClick: () -> Unit) {
    Surface(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        color = SubLokaColors.Surface,
        shape = RoundedCornerShape(12.dp),
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Surface(
                color = SubLokaColors.SurfaceHigh,
                shape = RoundedCornerShape(8.dp),
            ) {
                Text("▶", modifier = Modifier.padding(horizontal = 24.dp, vertical = 20.dp))
            }
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(project.title, style = MaterialTheme.typography.titleMedium)
                Text(
                    "${project.sourceLanguage.label} → ${project.sourceLanguage.target.label}",
                    color = SubLokaColors.TextSecondary,
                    style = MaterialTheme.typography.bodySmall,
                )
                Text(
                    "${project.durationLabel} · ${project.resolutionLabel} · ${project.lastEditedLabel}",
                    color = SubLokaColors.TextSecondary,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
}
