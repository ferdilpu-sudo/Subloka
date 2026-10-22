package app.subloka.feature.projects

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.style.TextOverflow
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
    Column(modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            item(key = "header") {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("SubLoka", style = MaterialTheme.typography.headlineMedium)
                    Text("Proyek saya", style = MaterialTheme.typography.titleLarge)
                    Text("Prototipe subtitle offline", color = SubLokaColors.TextSecondary,
                        style = MaterialTheme.typography.bodySmall)
                }
            }
            if (projects.isEmpty()) {
                item(key = "empty") {
                    Column(Modifier.padding(vertical = 24.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Belum ada proyek", style = MaterialTheme.typography.titleMedium)
                        Text("Mulai dengan memilih video. Setelah model siap, buat dan koreksi subtitle langsung di perangkat.",
                            color = SubLokaColors.TextSecondary)
                    }
                }
            } else {
                item(key = "count") {
                    Text("${projects.size} proyek · terakhir diperbarui", style = MaterialTheme.typography.labelLarge,
                        color = SubLokaColors.TextSecondary)
                }
                items(projects, key = { it.id }) { project ->
                    ProjectCard(project) { onOpenProject(project) }
                }
            }
        }
        PrimaryAction("Proyek baru", onNewProject, Modifier.fillMaxWidth())
    }
}

@Composable
private fun ProjectCard(project: ProjectSummary, onClick: () -> Unit) {
    Surface(
        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
            .clickable(role = Role.Button, onClickLabel = "Buka proyek ${project.title}", onClick = onClick),
        color = SubLokaColors.Surface,
        shape = RoundedCornerShape(12.dp),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(project.title, style = MaterialTheme.typography.titleMedium,
                maxLines = 2, overflow = TextOverflow.Ellipsis)
            if (project.sourceFileName != project.title) {
                Text(project.sourceFileName, style = MaterialTheme.typography.bodySmall,
                    maxLines = 2, overflow = TextOverflow.Ellipsis, color = SubLokaColors.TextSecondary)
            }
            Text("Audio ${project.sourceLanguage.label} · ${project.durationLabel}",
                style = MaterialTheme.typography.bodyMedium)
            Text("${project.resolutionLabel} · ${project.lastEditedLabel}",
                style = MaterialTheme.typography.bodySmall, color = SubLokaColors.TextSecondary)
            Text(project.statusLabel, style = MaterialTheme.typography.labelLarge, color = SubLokaColors.Primary)
        }
    }
}
