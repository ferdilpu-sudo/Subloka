package app.subloka.core.domain

data class EditorMutation<T>(
    val value: T,
    val contentRevision: Long,
)
