package app.subloka

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
internal fun RelinkVideoScreen(sourceName: String, busy: Boolean, message: String?,
    onPick: () -> Unit, onBack: () -> Unit, modifier: Modifier = Modifier) {
    Column(modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text("Tautkan ulang video", style = MaterialTheme.typography.headlineSmall)
        Text("Sumber proyek: $sourceName")
        Text("Pilih file asli yang sama, termasuk salinannya jika lokasinya berubah. Video yang berbeda atau sudah diedit akan ditolak.")
        Text("Caption, koreksi, timing, dan style yang tersimpan tetap dipertahankan.")
        message?.let { Text(it) }
        if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
        Button(onClick = onPick, enabled = !busy) { Text("Pilih video asli") }
        TextButton(onClick = onBack, enabled = !busy) { Text("Kembali ke editor") }
    }
}
