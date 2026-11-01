package app.subloka.feature.editor

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.SecondaryAction
import app.subloka.core.designsystem.SubLokaColors
import app.subloka.core.domain.CaptionSegment

/**
 * Present the existing timing guards as two distinct boundary controls.
 * Both buttons and bounds still use the existing microsecond model; no timing policy changes.
 */
@Composable
fun TimingWorkspace(segment: CaptionSegment, minimumStartUs: Long, maximumEndUs: Long,
                    onChange: (Long, Long) -> Unit, modifier: Modifier = Modifier,
                    navigation: @Composable () -> Unit = {}) {
    Column(
        modifier.verticalScroll(rememberScrollState()).padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        navigation()
        Text("Waktu caption", style = MaterialTheme.typography.titleMedium)
        Surface(
            color = SubLokaColors.Surface,
            shape = RoundedCornerShape(12.dp),
            border = BorderStroke(1.dp, SubLokaColors.SurfaceHigh),
        ) {
            Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("CAPTION TERPILIH", style = MaterialTheme.typography.labelSmall,
                    color = SubLokaColors.Primary)
                Text(segment.sourceText, style = MaterialTheme.typography.bodyMedium)
            }
        }
        Surface(
            color = SubLokaColors.Surface,
            shape = RoundedCornerShape(12.dp),
            border = BorderStroke(1.dp, SubLokaColors.SurfaceHigh),
        ) {
            Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Awal: ${formatTime(segment.startUs)}", style = MaterialTheme.typography.titleSmall)
                NudgeButtons("awal", canNudge = { delta ->
                    segment.startUs + delta >= minimumStartUs && segment.startUs + delta < segment.endUs
                }) { delta ->
                    val start = segment.startUs + delta
                    if (start >= minimumStartUs && start < segment.endUs) onChange(start, segment.endUs)
                }
            }
        }
        Surface(
            color = SubLokaColors.Surface,
            shape = RoundedCornerShape(12.dp),
            border = BorderStroke(1.dp, SubLokaColors.SurfaceHigh),
        ) {
            Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Akhir: ${formatTime(segment.endUs)}", style = MaterialTheme.typography.titleSmall)
                NudgeButtons("akhir", canNudge = { delta ->
                    segment.endUs + delta > segment.startUs && segment.endUs + delta <= maximumEndUs
                }) { delta ->
                    val end = segment.endUs + delta
                    if (end > segment.startUs && end <= maximumEndUs) onChange(segment.startUs, end)
                }
            }
        }
        Text("Perubahan berhenti pada batas video dan caption tetangga. Pilih caption untuk memutar dari awalnya.",
            color = SubLokaColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun NudgeButtons(boundary: String, canNudge: (Long) -> Boolean, onNudge: (Long) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        listOf(listOf(-100L, -10L), listOf(10L, 100L)).forEach { values ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                values.forEach { ms ->
                    SecondaryAction("${if (ms > 0) "+" else ""}$ms ms", { onNudge(ms * 1000) },
                        enabled = canNudge(ms * 1000), modifier = Modifier.weight(1f).semantics {
                            contentDescription = "Geser $boundary caption ${if (ms < 0) "lebih awal" else "lebih akhir"} ${kotlin.math.abs(ms)} milidetik"
                        })
                }
            }
        }
    }
}
