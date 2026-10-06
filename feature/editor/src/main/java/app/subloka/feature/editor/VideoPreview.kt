package app.subloka.feature.editor

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.SubLokaColors
import app.subloka.core.domain.CaptionSegment

@Composable
fun VideoPreview(
    segment: CaptionSegment?,
    compactHeight: Boolean,
    modifier: Modifier = Modifier,
) {
    val maxHeight = if (compactHeight) 112.dp else 248.dp
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(max = maxHeight)
                .aspectRatio(16f / 9f)
                .background(SubLokaColors.SurfaceHigh),
            contentAlignment = Alignment.Center,
        ) {
            Text("VIDEO PREVIEW · DEMO", color = SubLokaColors.TextSecondary)
            if (segment != null) {
                Column(
                    modifier = Modifier.align(Alignment.BottomCenter).padding(horizontal = 16.dp, vertical = 14.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(segment.sourceText, color = SubLokaColors.TextPrimary, style = MaterialTheme.typography.bodyMedium)
                    Text(segment.translationText, color = SubLokaColors.Warning, style = MaterialTheme.typography.bodySmall)
                }
            }
        }
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("▶  01:24.20", style = MaterialTheme.typography.bodySmall)
            Text("03:42", color = SubLokaColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
        }
    }
}
