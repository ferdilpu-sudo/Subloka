package app.subloka.feature.projects

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.PrimaryAction
import app.subloka.core.designsystem.SubLokaColors
import app.subloka.core.domain.ProjectSummary

/**
 * AutoCap Desktop-inspired information hierarchy in a compact Android layout.
 * Keep the existing project callbacks, accessible list and persistent primary action.
 * Model provisioning and active editor remain in their existing destinations.
 */
@Composable
fun ProjectsScreen(
    projects: List<ProjectSummary>,
    onNewProject: () -> Unit,
    onOpenProject: (ProjectSummary) -> Unit,
    modifier: Modifier = Modifier,
    onOpenInformation: () -> Unit = {},
) {
    Column(
        modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            item(key = "header") {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("SUBLOKA  /  STUDIO OFFLINE", style = MaterialTheme.typography.labelMedium,
                        color = SubLokaColors.Primary)
                    Text("Proyek saya", style = MaterialTheme.typography.headlineMedium)
                    Text("Buat, tinjau, dan koreksi caption dari video di perangkat.",
                        style = MaterialTheme.typography.bodyMedium, color = SubLokaColors.TextSecondary)
                    TextButton(onClick = onOpenInformation) { Text("Privasi dan lisensi") }
                }
            }
            item(key = "getting-started") {
                Surface(
                    color = SubLokaColors.Surface,
                    shape = RoundedCornerShape(16.dp),
                    border = BorderStroke(1.dp, SubLokaColors.SurfaceHigh),
                ) {
                    Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Mulai dari video", style = MaterialTheme.typography.titleMedium)
                        Text("Pilih video lokal, buat subtitle, kemudian rapikan hasilnya di editor.",
                            style = MaterialTheme.typography.bodyMedium)
                        Text("Impor video lewat tombol Proyek baru di bawah. Model hanya perlu disiapkan saat dibutuhkan.",
                            style = MaterialTheme.typography.bodySmall, color = SubLokaColors.TextSecondary)
                    }
                }
            }
            item(key = "recent-heading") {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("Proyek terbaru", style = MaterialTheme.typography.titleLarge)
                    Text(
                        if (projects.isEmpty()) "Belum ada riwayat proyek."
                        else "${projects.size} proyek tersimpan di perangkat",
                        color = SubLokaColors.TextSecondary,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
            if (projects.isEmpty()) {
                item(key = "empty") {
                    Surface(
                        color = SubLokaColors.Surface,
                        shape = RoundedCornerShape(16.dp),
                    ) {
                        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("Belum ada proyek", style = MaterialTheme.typography.titleMedium)
                            Text("Mulai dengan memilih video. Hasil dan koreksi caption akan tersedia di daftar ini.",
                                style = MaterialTheme.typography.bodyMedium, color = SubLokaColors.TextSecondary)
                        }
                    }
                }
            } else {
                items(projects, key = { it.id }) { project ->
                    ProjectCard(project) { onOpenProject(project) }
                }
            }
        }
        // One clear CTA stays visible on compact/large-font screens and with long project lists.
        PrimaryAction("Proyek baru", onNewProject, Modifier.fillMaxWidth())
    }
}

@Composable
private fun ProjectCard(project: ProjectSummary, onClick: () -> Unit) {
    Surface(
        modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp)
            .clickable(role = Role.Button, onClickLabel = "Buka proyek ${project.title}", onClick = onClick),
        color = SubLokaColors.Surface,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, SubLokaColors.SurfaceHigh),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.Top,
            ) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(project.title, style = MaterialTheme.typography.titleMedium,
                        maxLines = 2, overflow = TextOverflow.Ellipsis)
                    if (project.id == "demo-traveling") {
                        Text("PROYEK CONTOH", style = MaterialTheme.typography.labelSmall,
                            color = SubLokaColors.Warning)
                    }
                    if (project.sourceFileName != project.title) {
                        Text(project.sourceFileName, style = MaterialTheme.typography.bodySmall,
                            maxLines = 2, overflow = TextOverflow.Ellipsis,
                            color = SubLokaColors.TextSecondary)
                    }
                }
                Text("Buka ›", style = MaterialTheme.typography.labelMedium, color = SubLokaColors.Primary)
            }
            Text("Audio ${project.sourceLanguage.label}  ·  ${project.durationLabel}  ·  ${project.resolutionLabel}",
                style = MaterialTheme.typography.bodySmall, color = SubLokaColors.TextSecondary)
            Text(project.lastEditedLabel, style = MaterialTheme.typography.bodySmall,
                color = SubLokaColors.TextSecondary)
            Surface(
                color = SubLokaColors.Primary.copy(alpha = 0.12f),
                shape = RoundedCornerShape(8.dp),
            ) {
                Text(project.statusLabel, modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                    style = MaterialTheme.typography.labelMedium, color = SubLokaColors.Primary)
            }
        }
    }
}
