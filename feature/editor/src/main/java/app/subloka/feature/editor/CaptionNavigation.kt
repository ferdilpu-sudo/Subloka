package app.subloka.feature.editor

import androidx.compose.foundation.layout.*
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.subloka.core.domain.CaptionSegment

/** Shared selection controls; choosing a caption also drives the existing video seek. */
@Composable
internal fun CaptionNavigation(segments: List<CaptionSegment>, selectedId: String, onSelect: (String) -> Unit) {
    val index = segments.indexOfFirst { it.id == selectedId }
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        TextButton(onClick = { segments.getOrNull(index - 1)?.let { onSelect(it.id) } },
            enabled = index > 0, modifier = Modifier.sizeIn(minWidth = 48.dp, minHeight = 48.dp)
                .semantics { contentDescription = "Caption sebelumnya" }) { Text("‹") }
        Text("Caption ${index + 1} dari ${segments.size}", modifier = Modifier.weight(1f),
            style = MaterialTheme.typography.labelLarge, textAlign = androidx.compose.ui.text.style.TextAlign.Center)
        TextButton(onClick = { segments.getOrNull(index + 1)?.let { onSelect(it.id) } },
            enabled = index >= 0 && index < segments.lastIndex,
            modifier = Modifier.sizeIn(minWidth = 48.dp, minHeight = 48.dp)
                .semantics { contentDescription = "Caption berikutnya" }) { Text("›") }
    }
}
