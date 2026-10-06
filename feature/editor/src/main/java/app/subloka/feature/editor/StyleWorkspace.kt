package app.subloka.feature.editor

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.SubLokaColors
import app.subloka.core.domain.CaptionDisplayMode
import app.subloka.core.domain.CaptionStyle

@Composable
fun StyleWorkspace(
    style: CaptionStyle,
    onStyleChange: (CaptionStyle) -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(modifier = modifier, color = SubLokaColors.Surface, shape = RoundedCornerShape(12.dp)) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text("Display", style = MaterialTheme.typography.titleSmall)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                CaptionDisplayMode.entries.forEach { mode ->
                    FilterChip(
                        selected = style.displayMode == mode,
                        onClick = { onStyleChange(style.copy(displayMode = mode)) },
                        label = { Text(mode.name.lowercase().replaceFirstChar { it.uppercase() }) },
                    )
                }
            }

            Text("Original size · ${style.sourceSizePercent}%")
            Slider(
                value = style.sourceSizePercent.toFloat(),
                onValueChange = { onStyleChange(style.copy(sourceSizePercent = it.toInt())) },
                valueRange = 70f..140f,
            )

            Text("Translation size · ${style.translationSizePercent}%")
            Slider(
                value = style.translationSizePercent.toFloat(),
                onValueChange = { onStyleChange(style.copy(translationSizePercent = it.toInt())) },
                valueRange = 70f..140f,
            )

            ToggleRow("Outline", style.outlineEnabled) { onStyleChange(style.copy(outlineEnabled = it)) }
            ToggleRow("Background", style.backgroundEnabled) { onStyleChange(style.copy(backgroundEnabled = it)) }

            Text("Position · bottom ${style.bottomPositionPercent}%")
            Slider(
                value = style.bottomPositionPercent.toFloat(),
                onValueChange = { onStyleChange(style.copy(bottomPositionPercent = it.toInt())) },
                valueRange = 8f..35f,
            )
            Text(
                "Safe-area guide dan warna final perlu diverifikasi terhadap frame video nyata.",
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
        Text(label)
        Switch(checked = checked, onCheckedChange = onCheckedChange)
    }
}
