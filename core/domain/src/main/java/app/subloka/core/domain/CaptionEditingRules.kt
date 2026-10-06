package app.subloka.core.domain

import kotlin.math.abs
import kotlin.math.roundToInt

object CaptionEditingRules {
    fun splitTextSuggestion(text: String, ratio: Double): Pair<String, String> {
        val normalized = text.trim()
        if (normalized.isEmpty()) return "" to ""
        if (normalized.length == 1) return normalized to ""

        val boundedRatio = ratio.coerceIn(0.05, 0.95)
        val target = (normalized.length * boundedRatio).roundToInt().coerceIn(1, normalized.lastIndex)

        var bestWhitespace = -1
        var bestDistance = Int.MAX_VALUE
        for (index in 1 until normalized.lastIndex) {
            if (normalized[index].isWhitespace()) {
                val distance = abs(index - target)
                if (distance < bestDistance) {
                    bestWhitespace = index
                    bestDistance = distance
                }
            }
        }

        val cut = if (bestWhitespace >= 1) bestWhitespace else target
        return normalized.substring(0, cut).trimEnd() to normalized.substring(cut).trimStart()
    }

    fun mergeText(left: String, right: String): String =
        listOf(left.trim(), right.trim()).filter { it.isNotEmpty() }.joinToString(" ")
}
