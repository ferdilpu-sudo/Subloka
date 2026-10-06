package app.subloka.core.designsystem

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

object SubLokaColors {
    val Canvas = Color(0xFF0F1115)
    val Surface = Color(0xFF181B21)
    val SurfaceHigh = Color(0xFF21252D)
    val TextPrimary = Color(0xFFF5F7FA)
    val TextSecondary = Color(0xFFAEB6C5)
    val Primary = Color(0xFFA7B5FF)
    val OnPrimary = Color(0xFF101216)
    val Success = Color(0xFF7EDBA6)
    val Warning = Color(0xFFFFD18B)
    val Error = Color(0xFFFFB4AB)
}

private val SubLokaScheme = darkColorScheme(
    primary = SubLokaColors.Primary,
    onPrimary = SubLokaColors.OnPrimary,
    background = SubLokaColors.Canvas,
    onBackground = SubLokaColors.TextPrimary,
    surface = SubLokaColors.Surface,
    onSurface = SubLokaColors.TextPrimary,
    surfaceVariant = SubLokaColors.SurfaceHigh,
    onSurfaceVariant = SubLokaColors.TextSecondary,
    error = SubLokaColors.Error,
)

@Composable
fun SubLokaTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = SubLokaScheme,
        typography = MaterialTheme.typography,
        content = content,
    )
}
