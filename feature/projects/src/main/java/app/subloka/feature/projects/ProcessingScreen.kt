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
    onBack: () -> Unit, modifier: Modifier = Modifier, stopping: Boolean = false,
) {
    Column(modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text("Transkripsi", style = MaterialTheme.typography.headlineSmall)
            Text(when {
                busy && stopping -> "Menghentikan transkripsi…"
                busy -> "Transkripsi sedang berjalan"
                error != null -> "Transkripsi belum selesai"
                completed -> "Caption siap diperiksa"
                else -> "Transkripsi tidak berjalan"
            }, style = MaterialTheme.typography.titleMedium)
            if (busy) LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            if (stage.isNotBlank()) Text(stage)
            if (error != null) Text(error, color = MaterialTheme.colorScheme.error)
            Text(when {
                busy && stopping -> "Tunggu proses berhenti sebelum memulai lagi."
                busy -> "Boleh berpindah aplikasi atau mematikan layar. Pantau proses lewat notifikasi jika izin notifikasi aktif."
                completed -> "Buka editor untuk memeriksa kata dan waktu caption."
                else -> "Tekan Coba lagi untuk memeriksa kesiapan model dan memulai ulang transkripsi."
            })
            if (busy && !stopping) Text("Jika proses aplikasi dihentikan Android, transkripsi perlu dimulai ulang.", style = MaterialTheme.typography.bodySmall)
            if (!busy) SecondaryAction("Kembali ke proyek", onBack)
        }
        if (busy) SecondaryAction(if (stopping) "Menghentikan…" else "Hentikan", onCancel,
            enabled = !stopping, modifier = Modifier.fillMaxWidth())
        else PrimaryAction(if (completed && error == null) "Buka editor" else "Coba lagi",
            if (completed && error == null) onOpenEditor else onRetry, modifier = Modifier.fillMaxWidth())
    }
}
