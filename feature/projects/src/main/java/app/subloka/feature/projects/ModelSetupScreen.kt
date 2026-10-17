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
    useTurbo: Boolean, onModelSelected: (Boolean) -> Unit,
    onImport: () -> Unit, onImportVad: () -> Unit, onDownload: () -> Unit, onReady: () -> Unit,
    onBack: () -> Unit, onCancel: () -> Unit, modifier: Modifier = Modifier,
) {
    Column(modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text("Siapkan caption offline", style = MaterialTheme.typography.headlineSmall)
        Text("Prototipe • caption bahasa asli. Terjemahan dapat dibuat dari editor setelah transkripsi. Ekspor SRT dan MP4 tersedia setelah caption disimpan.")
        Text("Pilih model caption", style = MaterialTheme.typography.titleMedium)
        SingleChoiceSegmentedButtonRow(modifier = Modifier.fillMaxWidth()) {
            SegmentedButton(selected = useTurbo, onClick = { onModelSelected(true) }, enabled = !busy,
                shape = SegmentedButtonDefaults.itemShape(0, 2)) { Text("Turbo") }
            SegmentedButton(selected = !useTurbo, onClick = { onModelSelected(false) }, enabled = !busy,
                shape = SegmentedButtonDefaults.itemShape(1, 2)) { Text("Base • ringan") }
        }
        Text(if (useTurbo) "Whisper Large-v3 Turbo • sekitar 574 MB. Kandidat pengganti untuk kualitas caption. Memakai lebih banyak memori; proses bisa lebih lama dari durasi video. Kecepatan dan kualitas di Sony belum terverifikasi. Mulai dengan video pendek."
            else "Whisper Base • sekitar 148 MB. Pilihan ringan sebelumnya; kesalahan kata masih dapat terjadi.")
        Text("Keduanya memerlukan pendeteksi ucapan Silero (kurang dari 1 MB). Model yang sudah terverifikasi dipakai kembali. Impor sesuai pilihan atau unduh yang belum tersedia. Unduhan memerlukan internet; video dan audio diproses di perangkat. Caption yang tersimpan tidak diganti.")
        Text(if (ready) "✓ Model terverifikasi dan siap" else "Model belum siap")
        if (busy) LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
        if (stage.isNotBlank()) Text(stage)
        if (error != null) Text(error, color = MaterialTheme.colorScheme.error)
        if (busy) SecondaryAction("Batalkan", onCancel)
        else {
            SecondaryAction(if (useTurbo) "Impor Whisper Turbo" else "Impor Whisper Base", onImport)
            SecondaryAction("Impor pendeteksi ucapan", onImportVad)
            SecondaryAction("Unduh model yang belum tersedia", onDownload)
            PrimaryAction("Mulai transkripsi", onReady, enabled = ready, modifier = Modifier.fillMaxWidth())
            SecondaryAction("Kembali", onBack)
        }
    }
}
