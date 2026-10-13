package app.subloka.feature.projects

import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.PrimaryAction
import app.subloka.core.designsystem.SecondaryAction

@Composable
fun ProcessingScreen(
    busy: Boolean, stage: String, error: String?, completed: Boolean,
    onCancel: () -> Unit, onRetry: () -> Unit, onOpenEditor: () -> Unit,
    onBack: () -> Unit, modifier: Modifier = Modifier,
) {
    Column(modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(18.dp)) {
        Text("Caption di perangkat", style = MaterialTheme.typography.headlineSmall)
        Text("Tetap buka aplikasi selama proses. Berpindah aplikasi atau mengunci layar menghentikan proses; Anda dapat mencoba lagi.")
        if (busy) LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
        Text(stage)
        if (error != null) Text(error, color = MaterialTheme.colorScheme.error)
        if (busy) SecondaryAction("Batalkan", onCancel)
        else {
            if (completed) PrimaryAction("Buka editor", onOpenEditor)
            else SecondaryAction("Coba lagi", onRetry)
            SecondaryAction("Kembali ke proyek", onBack)
        }
    }
}
