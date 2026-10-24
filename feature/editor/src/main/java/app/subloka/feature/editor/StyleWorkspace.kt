package app.subloka.feature.editor

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.SubLokaColors
import app.subloka.core.domain.CaptionDisplayMode
import app.subloka.core.domain.CaptionStyle
import app.subloka.core.domain.CaptionOrder

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun StyleWorkspace(
    style: CaptionStyle,
    onStyleChange: (CaptionStyle) -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(modifier = modifier, color = SubLokaColors.Surface, shape = RoundedCornerShape(12.dp)) {
        Column(modifier = Modifier.verticalScroll(rememberScrollState()).padding(14.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text("Tampilan subtitle", style = MaterialTheme.typography.titleSmall)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                CaptionDisplayMode.entries.forEach { mode ->
                    FilterChip(
                        selected = style.displayMode == mode,
                        onClick = { onStyleChange(style.copy(displayMode = mode)) },
                        label = { Text(when (mode) {
                            CaptionDisplayMode.DUAL -> "Dua bahasa"
                            CaptionDisplayMode.ORIGINAL -> "Teks asli"
                            CaptionDisplayMode.TRANSLATION -> "Terjemahan"
                        }) },
                    )
                }
            }

            ToggleRow("Terjemahan di atas", style.order == CaptionOrder.TRANSLATION_FIRST) {
                onStyleChange(style.copy(order = if (it) CaptionOrder.TRANSLATION_FIRST else CaptionOrder.SOURCE_FIRST))
            }
            Text("Ukuran teks asli · ${style.sourceSizePercent}%")
            Slider(
                value = style.sourceSizePercent.toFloat(),
                onValueChange = { onStyleChange(style.copy(sourceSizePercent = it.toInt())) },
                valueRange = 70f..140f,
            )

            Text("Ukuran terjemahan · ${style.translationSizePercent}%")
            Slider(
                value = style.translationSizePercent.toFloat(),
                onValueChange = { onStyleChange(style.copy(translationSizePercent = it.toInt())) },
                valueRange = 70f..140f,
            )

            ToggleRow("Garis tepi", style.outlineEnabled) { onStyleChange(style.copy(outlineEnabled = it)) }
            ToggleRow("Latar subtitle", style.backgroundEnabled) { onStyleChange(style.copy(backgroundEnabled = it)) }

            Text("Jarak dari bawah · ${style.bottomPositionPercent}%")
            Slider(
                value = style.bottomPositionPercent.toFloat(),
                onValueChange = { onStyleChange(style.copy(bottomPositionPercent = it.toInt())) },
                valueRange = 8f..35f,
            )
            Text(
                "Preview dan MP4 memakai tata letak yang sama. Caption terlalu panjang harus dipecah sebelum ekspor.",
                color = SubLokaColors.TextSecondary,
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

@Composable
private fun ToggleRow(label: String, checked: Boolean, onCheckedChange: (Boolean) -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label, modifier = Modifier.weight(1f).padding(end = 12.dp))
        Switch(checked = checked, onCheckedChange = onCheckedChange)
    }
}
