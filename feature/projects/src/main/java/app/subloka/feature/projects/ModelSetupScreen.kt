package app.subloka.feature.projects

import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
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
    var advanced by rememberSaveable { mutableStateOf(false) }
    Column(modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            TextButton(onClick = onBack, enabled = !busy) { Text("Kembali ke proyek") }
            Text("Siapkan caption offline", style = MaterialTheme.typography.headlineSmall)
            Text("Langkah 2 dari 2 · Kesiapan model")
            Text("Model diperlukan untuk mengenali ucapan di perangkat. Setelah model siap, transkripsi dapat berjalan tanpa internet.")
            Text("Pilih model caption", style = MaterialTheme.typography.titleMedium)
            SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                SegmentedButton(selected = useTurbo, onClick = { onModelSelected(true) }, enabled = !busy,
                    shape = SegmentedButtonDefaults.itemShape(0, 2)) { Text("Turbo") }
                SegmentedButton(selected = !useTurbo, onClick = { onModelSelected(false) }, enabled = !busy,
                    shape = SegmentedButtonDefaults.itemShape(1, 2)) { Text("Base · ringan") }
            }
            Text(if (useTurbo) "Turbo · sekitar 574 MB. Membutuhkan lebih banyak memori; proses dapat lebih lama dari durasi video."
                else "Base · sekitar 148 MB. Lebih ringan; hasil caption tetap perlu dikoreksi.")
            Text(if (ready) "✓ Model siap digunakan" else "Model belum siap", style = MaterialTheme.typography.titleMedium)
            Text(if (ready) "Model yang sudah tersimpan akan digunakan kembali."
                else "Unduh model yang belum tersedia atau impor dari file. Keduanya memerlukan pendeteksi ucapan, kurang dari 1 MB.")
            if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
            if (stage.isNotBlank()) Text(stage)
            if (error != null) Text(error, color = MaterialTheme.colorScheme.error)
            TextButton(onClick = { advanced = !advanced }) { Text(if (advanced) "Tutup opsi lanjutan" else "Opsi lanjutan · impor model") }
            if (advanced) {
                Text(if (useTurbo) "Whisper Large-v3 Turbo + Silero" else "Whisper Base + Silero")
                SecondaryAction("Impor model caption", onImport, enabled = !busy, modifier = Modifier.fillMaxWidth())
                SecondaryAction("Impor pendeteksi ucapan", onImportVad, enabled = !busy, modifier = Modifier.fillMaxWidth())
            }
            Text("Video dan audio diproses di perangkat. Terjemahan tersedia dari editor setelah transkripsi.", style = MaterialTheme.typography.bodySmall)
        }
        if (busy) SecondaryAction("Batalkan", onCancel, modifier = Modifier.fillMaxWidth())
        else PrimaryAction(
            if (ready) "Mulai transkripsi" else if (error != null) "Coba unduh lagi" else "Unduh model yang diperlukan",
            onClick = { if (ready) onReady() else onDownload() }, modifier = Modifier.fillMaxWidth())
    }
}
