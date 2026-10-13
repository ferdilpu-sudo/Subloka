package app.subloka.feature.projects

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.PrimaryAction
import app.subloka.core.designsystem.SecondaryAction

@Composable
fun TranslationSetupScreen(ready: Boolean, busy: Boolean, stage: String, error: String?,
                           eligibleCount: Int, pairLabel: String,
                           onCheck: () -> Unit, onDownload: (Boolean) -> Unit,
                           onTranslate: () -> Unit, onCancel: () -> Unit, onBack: () -> Unit,
                           modifier: Modifier = Modifier) {
    var wifiOnly by rememberSaveable { mutableStateOf(true) }
    Column(modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text("Terjemahan offline", style = MaterialTheme.typography.headlineSmall)
        Text("$pairLabel • $eligibleCount caption dapat diterjemahkan")
        Text("Teks asli tetap disimpan. Terjemahan manual dan hasil yang sudah terbaru dilewati. Periksa makna hasil terjemahan sebelum digunakan.")
        Text(if (ready) "✓ Model siap di perangkat" else "Model terjemahan belum siap")
        if (busy) LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
        if (stage.isNotBlank()) Text(stage)
        if (error != null) Text(error, color = MaterialTheme.colorScheme.error)
        if (busy) {
            Text("Tetap buka aplikasi. Berpindah aplikasi menghentikan proses; hasil yang sudah tersimpan tetap tersedia.")
            SecondaryAction("Hentikan", onCancel)
        } else {
            if (!ready) {
                Text("Unduh model sekali dengan internet. Setelah siap, terjemahan diproses di perangkat tanpa koneksi. Model ini terpisah dari Whisper.")
                Row { Checkbox(wifiOnly, { wifiOnly = it }); Text("Unduh hanya melalui Wi-Fi", modifier = Modifier.padding(top = 12.dp)) }
                PrimaryAction("Unduh model terjemahan", { onDownload(wifiOnly) })
            } else {
                PrimaryAction("Terjemahkan caption", onTranslate, enabled = eligibleCount > 0)
            }
            SecondaryAction("Periksa model kembali", onCheck)
            SecondaryAction("Kembali ke editor", onBack)
        }
    }
}
