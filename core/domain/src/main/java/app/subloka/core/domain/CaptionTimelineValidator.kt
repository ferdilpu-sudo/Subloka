package app.subloka.core.domain

object CaptionTimelineValidator {
    fun validate(projectDurationUs: Long, segments: List<CaptionSegment>) {
        require(projectDurationUs > 0) { "projectDurationUs must be positive" }

        val ordered = segments.sortedWith(compareBy<CaptionSegment> { it.startUs }.thenBy { it.id })
        ordered.forEach { segment ->
            require(segment.endUs <= projectDurationUs) {
                "segment ${segment.id} exceeds project duration"
            }
        }

        for (index in 1 until ordered.size) {
            val previous = ordered[index - 1]
            val current = ordered[index]
            require(previous.endUs <= current.startUs) {
                "segments ${previous.id} and ${current.id} overlap"
            }
        }
    }
}
