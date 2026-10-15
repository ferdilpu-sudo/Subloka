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
    onImport: () -> Unit, onImportVad: () -> Unit, onDownload: () -> Unit, onReady: () -> Unit,
    onBack: () -> Unit, onCancel: () -> Unit, modifier: Modifier = Modifier,
) {
    Column(modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text("Siapkan caption offline", style = MaterialTheme.typography.headlineSmall)
        Text("Prototipe • caption bahasa asli. Terjemahan dapat dibuat dari editor setelah transkripsi. Ekspor SRT dan MP4 tersedia setelah caption disimpan.")
        Text("Caption memerlukan Whisper Base (sekitar 148 MB) dan pendeteksi ucapan Silero (kurang dari 1 MB). Impor keduanya atau unduh model yang belum tersedia. Model lama yang terverifikasi tetap dipakai. Unduhan memerlukan internet; video dan audio diproses di perangkat.")
        Text(if (ready) "✓ Model terverifikasi dan siap" else "Model belum siap")
        if (busy) LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
        if (stage.isNotBlank()) Text(stage)
        if (error != null) Text(error, color = MaterialTheme.colorScheme.error)
        if (busy) SecondaryAction("Batalkan", onCancel)
        else {
            SecondaryAction("Impor Whisper Base", onImport)
            SecondaryAction("Impor pendeteksi ucapan", onImportVad)
            SecondaryAction("Unduh model yang belum tersedia", onDownload)
            PrimaryAction("Mulai transkripsi", onReady, enabled = ready, modifier = Modifier.fillMaxWidth())
            SecondaryAction("Kembali", onBack)
        }
    }
}
