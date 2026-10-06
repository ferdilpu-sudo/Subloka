package app.subloka.core.domain

data class ProjectSummary(
    val id: String,
    val title: String,
    val sourceFileName: String,
    val sourceLanguage: SourceLanguage,
    val durationLabel: String,
    val resolutionLabel: String,
    val lastEditedLabel: String,
)

enum class ModelState {
    READY,
    NOT_READY,
    DOWNLOADING,
    FAILED,
}

enum class ProcessingStageState {
    WAITING,
    ACTIVE,
    COMPLETE,
    FAILED,
}

data class ProcessingStage(
    val label: String,
    val state: ProcessingStageState,
)
