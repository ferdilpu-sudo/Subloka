package app.subloka.core.designsystem

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun PrimaryAction(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.defaultMinSize(minHeight = 48.dp),
        shape = RoundedCornerShape(8.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = SubLokaColors.Primary,
            contentColor = SubLokaColors.OnPrimary,
        ),
    ) {
        Text(text)
    }
}

@Composable
fun SecondaryAction(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    OutlinedButton(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.defaultMinSize(minHeight = 48.dp),
        shape = RoundedCornerShape(8.dp),
        border = BorderStroke(1.dp, SubLokaColors.SurfaceHigh),
    ) {
        Text(text)
    }
}

@Composable
fun DemoBadge(modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier,
        color = SubLokaColors.Warning.copy(alpha = 0.16f),
        contentColor = SubLokaColors.Warning,
        shape = RoundedCornerShape(999.dp),
    ) {
        Text(
            text = "DEMO · engine belum terhubung",
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
            style = androidx.compose.material3.MaterialTheme.typography.labelMedium,
        )
    }
}

@Composable
fun InlineStatus(
    text: String,
    symbol: String,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(symbol)
        Text(text, style = androidx.compose.material3.MaterialTheme.typography.bodySmall)
    }
}
