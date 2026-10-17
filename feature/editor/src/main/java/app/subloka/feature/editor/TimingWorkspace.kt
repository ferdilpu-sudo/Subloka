package app.subloka.feature.editor

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.SecondaryAction
import app.subloka.core.domain.CaptionSegment

@Composable
fun TimingWorkspace(segment: CaptionSegment, minimumStartUs: Long, maximumEndUs: Long,
                    onChange: (Long, Long) -> Unit, modifier: Modifier = Modifier) {
    Column(modifier.verticalScroll(rememberScrollState()).padding(14.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("Waktu caption", style = MaterialTheme.typography.titleMedium)
        Text("Awal: ${formatTime(segment.startUs)}")
        NudgeButtons { delta ->
            val start = segment.startUs + delta
            if (start >= minimumStartUs && start < segment.endUs) onChange(start, segment.endUs)
        }
        Text("Akhir: ${formatTime(segment.endUs)}")
        NudgeButtons { delta ->
            val end = segment.endUs + delta
            if (end > segment.startUs && end <= maximumEndUs) onChange(segment.startUs, end)
        }
        Text("Perubahan berhenti pada batas video dan caption tetangga. Pilih caption untuk memutar dari awalnya.")
    }
}

@Composable
private fun NudgeButtons(onNudge: (Long) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        listOf(listOf(-100L, -10L), listOf(10L, 100L)).forEach { values ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                values.forEach { ms ->
                    SecondaryAction("${if (ms > 0) "+" else ""}$ms ms", { onNudge(ms * 1000) }, modifier = Modifier.weight(1f))
                }
            }
        }
    }
}
