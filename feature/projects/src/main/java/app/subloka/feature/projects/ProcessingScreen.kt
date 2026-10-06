package app.subloka.feature.projects

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.DemoBadge
import app.subloka.core.designsystem.SecondaryAction
import app.subloka.core.designsystem.SubLokaColors
import app.subloka.core.domain.ProcessingStage
import app.subloka.core.domain.ProcessingStageState

@Composable
fun ProcessingScreen(
    stages: List<ProcessingStage>,
    onCancel: () -> Unit,
    onDemoComplete: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        Text("Membuat caption di perangkat", style = MaterialTheme.typography.headlineSmall)
        DemoBadge()
        Text(
            "State ini hanya mensimulasikan flow. Tidak ada audio yang sedang ditranskripsi.",
            color = SubLokaColors.TextSecondary,
        )

        Surface(color = SubLokaColors.Surface, shape = RoundedCornerShape(12.dp)) {
            Column(modifier = Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                stages.forEach { stage ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(stage.label)
                        Text(stageSymbol(stage.state), color = stageColor(stage.state))
                    }
                }
            }
        }

        Text("Progress numerik sengaja tidak dibuat-buat pada demo.", color = SubLokaColors.TextSecondary)

        SecondaryAction("Batalkan", onCancel, modifier = Modifier.fillMaxWidth())
        SecondaryAction("Selesaikan demo", onDemoComplete, modifier = Modifier.fillMaxWidth())
    }
}

private fun stageSymbol(state: ProcessingStageState): String = when (state) {
    ProcessingStageState.WAITING -> "○ Menunggu"
    ProcessingStageState.ACTIVE -> "● Aktif"
    ProcessingStageState.COMPLETE -> "✓ Selesai"
    ProcessingStageState.FAILED -> "! Gagal"
}

private fun stageColor(state: ProcessingStageState) = when (state) {
    ProcessingStageState.COMPLETE -> SubLokaColors.Success
    ProcessingStageState.FAILED -> SubLokaColors.Error
    ProcessingStageState.ACTIVE -> SubLokaColors.Primary
    ProcessingStageState.WAITING -> SubLokaColors.TextSecondary
}
