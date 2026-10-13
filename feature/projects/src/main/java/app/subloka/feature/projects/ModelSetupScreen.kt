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
fun ModelSetupScreen(
    ready: Boolean, busy: Boolean, stage: String, error: String?,
    onImport: () -> Unit, onDownload: () -> Unit, onReady: () -> Unit,
    onBack: () -> Unit, onCancel: () -> Unit, modifier: Modifier = Modifier,
) {
    Column(modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text("Siapkan caption offline", style = MaterialTheme.typography.headlineSmall)
        Text("Prototipe • caption bahasa asli. Terjemahan otomatis dan ekspor belum tersedia.")
        Text("Impor ggml-base.bin atau unduh model Whisper Base (sekitar 148 MB). Unduhan memerlukan internet; video dan audio diproses di perangkat.")
        Text(if (ready) "✓ Model terverifikasi dan siap" else "Model belum siap")
        if (busy) LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
        if (stage.isNotBlank()) Text(stage)
        if (error != null) Text(error, color = MaterialTheme.colorScheme.error)
        if (busy) SecondaryAction("Batalkan", onCancel)
        else {
            SecondaryAction("Impor model dari perangkat", onImport)
            SecondaryAction("Unduh model", onDownload)
            PrimaryAction("Mulai transkripsi", onReady, enabled = ready, modifier = Modifier.fillMaxWidth())
            SecondaryAction("Kembali", onBack)
        }
    }
}
