package app.subloka.feature.projects

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.DemoBadge
import app.subloka.core.designsystem.PrimaryAction
import app.subloka.core.designsystem.SubLokaColors

@Composable
fun ModelSetupScreen(
    onReady: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var step by remember { mutableIntStateOf(0) }

    Column(
        modifier = modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        Text("Siapkan Caption Offline", style = MaterialTheme.typography.headlineSmall)
        DemoBadge()
        Text(
            "Aplikasi membutuhkan model bahasa agar caption dan translation dapat diproses di perangkat. Video dan audio tidak diunggah.",
            color = SubLokaColors.TextSecondary,
        )

        ModelRow("Model caption", ready = step >= 1)
        ModelRow("English–Indonesia", ready = step >= 2)

        if (step in 1..1) {
            LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            Text("Menyiapkan model… ukuran belum diklaim pada demo.", color = SubLokaColors.TextSecondary)
        }

        PrimaryAction(
            text = if (step >= 2) "Lanjut" else "Siapkan Offline",
            onClick = {
                when {
                    step == 0 -> step = 1
                    step == 1 -> step = 2
                    else -> onReady()
                }
            },
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

@Composable
private fun ModelRow(label: String, ready: Boolean) {
    Surface(color = SubLokaColors.Surface, shape = RoundedCornerShape(10.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(14.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(label)
            Text(if (ready) "✓ Ready" else "Download", color = if (ready) SubLokaColors.Success else SubLokaColors.Primary)
        }
    }
}
