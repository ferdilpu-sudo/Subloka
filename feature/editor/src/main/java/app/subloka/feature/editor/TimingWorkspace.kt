package app.subloka.feature.editor

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.SecondaryAction
import app.subloka.core.designsystem.SubLokaColors
import app.subloka.core.domain.CaptionSegment

@Composable
fun TimingWorkspace(segment: CaptionSegment, modifier: Modifier = Modifier) {
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Surface(color = SubLokaColors.Surface, shape = RoundedCornerShape(12.dp)) {
            Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                Text("Timeline · contextual", style = MaterialTheme.typography.titleSmall)
                Box(
                    modifier = Modifier.fillMaxWidth().height(54.dp).background(SubLokaColors.SurfaceHigh),
                    contentAlignment = Alignment.Center,
                ) {
                    Text("─────────│────────────────", color = SubLokaColors.Primary)
                }
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    TimeField("Start", formatTime(segment.startUs))
                    TimeField("End", formatTime(segment.endUs))
                }
                Text("Nudge start/end", color = SubLokaColors.TextSecondary, style = MaterialTheme.typography.labelMedium)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("-100 ms", "-10 ms", "+10 ms", "+100 ms").forEach { label ->
                        SecondaryAction(label, onClick = {}, modifier = Modifier.weight(1f))
                    }
                }
                Text(
                    "Drag bukan satu-satunya kontrol. Input waktu dan nudge tetap tersedia.",
                    color = SubLokaColors.TextSecondary,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
}

@Composable
private fun TimeField(label: String, value: String) {
    Column {
        Text(label, color = SubLokaColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
        Text(value, style = MaterialTheme.typography.titleMedium)
    }
}
