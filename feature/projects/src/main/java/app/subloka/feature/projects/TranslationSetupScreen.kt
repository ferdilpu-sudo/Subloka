package app.subloka.feature.projects

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.PrimaryAction
import app.subloka.core.designsystem.SecondaryAction

@Composable
fun TranslationSetupScreen(ready: Boolean, busy: Boolean, stage: String, error: String?,
                           recoveryCount: Int, hasRecovery: Boolean, onResume: () -> Unit, onDiscardRecovery: () -> Unit,
                           eligibleCount: Int, replaceableCount: Int, pairLabel: String,
                           useGemma: Boolean, termsAccepted: Boolean,
                           onModelSelected: (Boolean) -> Unit, onTermsAccepted: (Boolean) -> Unit,
                           onImport: () -> Unit,
                           onCheck: () -> Unit, onDownload: (Boolean) -> Unit,
                           onTranslate: (Boolean) -> Unit, onCancel: () -> Unit, onBack: () -> Unit,
                           backgroundRunning: Boolean = false, modifier: Modifier = Modifier, stopping: Boolean = false) {
    var wifiOnly by rememberSaveable { mutableStateOf(true) }
    var replaceMachine by rememberSaveable { mutableStateOf(false) }
    var confirmDiscard by remember { mutableStateOf(false) }
    var advanced by rememberSaveable { mutableStateOf(false) }
    var showTerms by remember { mutableStateOf(false) }
    val context = LocalContext.current
    val permitted = !useGemma || termsAccepted
    val count = if (hasRecovery) recoveryCount else if (replaceMachine) replaceableCount else eligibleCount
    if (confirmDiscard) {
        AlertDialog(onDismissRequest = { confirmDiscard = false }, title = { Text("Hapus antrean tertunda?") },
            text = { Text("Caption dan hasil terjemahan tetap tersimpan. Setelah ini kamu bisa memilih model atau membuat antrean baru.") },
            confirmButton = { TextButton(onClick = { confirmDiscard = false; onDiscardRecovery() }) { Text("Hapus antrean") } },
            dismissButton = { TextButton(onClick = { confirmDiscard = false }) { Text("Kembali") } })
    }
    if (showTerms) {
        val terms by produceState("Memuat ketentuan…") {
            value = withContext(Dispatchers.IO) {
                try {
                    listOf("Gemma-terms.txt", "Gemma-prohibited_use_policy.txt").joinToString("\n\n") { file ->
                        context.assets.open("licenses/$file").bufferedReader().use { it.readText() }
                    }
                } catch (_: Exception) { "Ketentuan tidak dapat dibuka. Jangan menyetujui sebelum membacanya di https://ai.google.dev/gemma/terms dan https://ai.google.dev/gemma/prohibited_use_policy." }
            }
        }
        AlertDialog(onDismissRequest = { showTerms = false }, title = { Text("Ketentuan Gemma") },
            text = { Text(terms, modifier = Modifier.heightIn(max = 400.dp).verticalScroll(rememberScrollState())) },
            confirmButton = { TextButton(onClick = { showTerms = false }) { Text("Tutup") } })
    }
    Column(modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text("Terjemahan offline", style = MaterialTheme.typography.headlineSmall)
            Text("$pairLabel • $count caption dapat diterjemahkan")
            Text(when {
                busy && stopping -> "Menghentikan terjemahan…"
                busy && backgroundRunning -> "Terjemahan sedang berjalan"
                busy -> "Menyiapkan model terjemahan"
                error != null -> "Perlu ditindaklanjuti"
                hasRecovery -> "Terjemahan dapat dilanjutkan"
                ready && count == 0 -> "Tidak ada caption yang perlu diterjemahkan"
                ready -> "Siap menerjemahkan"
                else -> "Siapkan model terlebih dahulu"
            }, style = MaterialTheme.typography.titleMedium)
            if (busy) LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            if (stage.isNotBlank()) Text(stage)
            if (error != null) Text(error, color = MaterialTheme.colorScheme.error)
            if (busy) Text(if (stopping) "Menunggu proses berhenti. Hasil yang sudah tersimpan tetap tersedia."
                else if (backgroundRunning) "Boleh berpindah aplikasi atau mematikan layar. Jika Android menghentikan aplikasi, buka proyek dan lanjutkan sisa terjemahan."
                else "Tetap buka aplikasi selama penyiapan model.")
            Text("Teks asli dan waktu caption tetap disimpan. Koreksi terjemahan manual selalu dilewati. Periksa makna hasil terjemahan sebelum digunakan.")
            Text(if (useGemma) "Model aktif: TranslateGemma" else "Model aktif: Google Translate (ML Kit) • ringan")
            TextButton(onClick = { advanced = !advanced }) {
                Text(if (advanced) "Tutup opsi lanjutan" else "Opsi lanjutan")
            }
            if (advanced) {
                Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    FilterChip(selected = useGemma, onClick = { onModelSelected(true) }, enabled = !busy && !hasRecovery,
                        label = { Text("TranslateGemma") })
                    FilterChip(selected = !useGemma, onClick = { onModelSelected(false) }, enabled = !busy && !hasRecovery,
                        label = { Text("ML Kit • ringan") })
                }
                if (!busy) {
                    if (useGemma && !ready) SecondaryAction("Impor model terjemahan", onImport, enabled = permitted)
                    SecondaryAction("Periksa model kembali", onCheck)
                }
            }
            if (useGemma) {
                Text("TranslateGemma 4B • unduhan 2,49 GB. Membutuhkan banyak RAM dan dapat lambat. Kecepatan bergantung pada perangkat dan panjang caption.")
                SecondaryAction("Baca ketentuan dan kebijakan Gemma", { showTerms = true })
                Row {
                    Checkbox(termsAccepted, onTermsAccepted, enabled = !busy)
                    Text("Saya telah membaca dan menyetujui ketentuan serta kebijakan Gemma.", Modifier.weight(1f).padding(top = 12.dp))
                }
            }
            if (!hasRecovery) Row {
                Checkbox(replaceMachine, { replaceMachine = it }, enabled = !busy)
                Text("Ganti juga hasil terjemahan otomatis yang sudah ada", Modifier.weight(1f).padding(top = 12.dp))
            }
            if (hasRecovery) Text("Ada pekerjaan terjemahan tertunda: $recoveryCount caption belum selesai. Lanjutkan dengan model yang sama; caption yang berubah atau dikoreksi manual akan dilewati.")
            Text(if (ready) "✓ Model siap di perangkat" else "Model terjemahan belum siap")
            if (!busy) {
                if (!ready) {
                    Text("Unduh model sekali dengan internet. Setelah siap, terjemahan diproses di perangkat tanpa koneksi. Model ini terpisah dari Whisper.")
                    Row { Checkbox(wifiOnly, { wifiOnly = it }); Text("Unduh hanya melalui Wi-Fi", modifier = Modifier.padding(top = 12.dp)) }
                }
                if (hasRecovery) SecondaryAction("Hapus antrean tertunda", { confirmDiscard = true })
                SecondaryAction("Kembali ke editor", onBack)
            }
        }
        when {
            busy -> SecondaryAction(if (stopping) "Menghentikan…" else "Hentikan", onCancel,
                enabled = !stopping, modifier = Modifier.fillMaxWidth())
            !ready -> PrimaryAction("Unduh model terjemahan", { onDownload(wifiOnly) }, enabled = permitted, modifier = Modifier.fillMaxWidth())
            hasRecovery -> PrimaryAction(if (useGemma) "Lanjutkan sisa terjemahan" else "Lanjutkan dengan Google", onResume, enabled = permitted, modifier = Modifier.fillMaxWidth())
            else -> PrimaryAction(if (useGemma) "Terjemahkan caption" else "Translate with Google", { onTranslate(replaceMachine) }, enabled = permitted && count > 0, modifier = Modifier.fillMaxWidth())
        }
    }
}
