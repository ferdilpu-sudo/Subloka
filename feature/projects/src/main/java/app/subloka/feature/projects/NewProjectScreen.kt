package app.subloka.feature.projects

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.DemoBadge
import app.subloka.core.designsystem.PrimaryAction
import app.subloka.core.designsystem.SubLokaColors
import app.subloka.core.domain.SourceLanguage

@Composable
fun NewProjectScreen(
    onBack: () -> Unit,
    onContinue: (SourceLanguage) -> Unit,
    modifier: Modifier = Modifier,
) {
    var videoSelected by remember { mutableStateOf(false) }
    var sourceLanguage by remember { mutableStateOf(SourceLanguage.ENGLISH) }

    Column(
        modifier = modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("‹", style = MaterialTheme.typography.headlineSmall, modifier = Modifier.clickable(onClick = onBack))
            Text("New Project", style = MaterialTheme.typography.headlineSmall)
        }

        DemoBadge()

        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = SubLokaColors.Surface,
            shape = RoundedCornerShape(12.dp),
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(if (videoSelected) "Traveling.mp4" else "Belum ada video", style = MaterialTheme.typography.titleMedium)
                Text(
                    if (videoSelected) "03:42 · 1080p · portrait" else "Pilih satu video dari perangkat.",
                    color = SubLokaColors.TextSecondary,
                )
            }
        }

        if (videoSelected) {
            Text("Bahasa audio", style = MaterialTheme.typography.titleMedium)
            LanguageRadio(SourceLanguage.ENGLISH, sourceLanguage == SourceLanguage.ENGLISH) { sourceLanguage = SourceLanguage.ENGLISH }
            LanguageRadio(SourceLanguage.INDONESIA, sourceLanguage == SourceLanguage.INDONESIA) { sourceLanguage = SourceLanguage.INDONESIA }

            Surface(color = SubLokaColors.SurfaceHigh, shape = RoundedCornerShape(8.dp)) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text("Caption akan dibuat", style = MaterialTheme.typography.labelMedium)
                    Text("${sourceLanguage.label} + ${sourceLanguage.target.label}")
                }
            }
        }

        PrimaryAction(
            text = if (videoSelected) "Buat Caption" else "Pilih video",
            onClick = {
                if (videoSelected) onContinue(sourceLanguage) else videoSelected = true
            },
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

@Composable
private fun LanguageRadio(language: SourceLanguage, selected: Boolean, onClick: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick).padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        RadioButton(selected = selected, onClick = onClick)
        Text(language.label)
    }
}
