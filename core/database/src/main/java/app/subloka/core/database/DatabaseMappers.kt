package app.subloka.core.database

import app.subloka.core.domain.CaptionDisplayMode
import app.subloka.core.domain.CaptionOrder
import app.subloka.core.domain.CaptionProject
import app.subloka.core.domain.CaptionSegment
import app.subloka.core.domain.CaptionStyle
import app.subloka.core.domain.SourceLanguage
import app.subloka.core.domain.TranslationOrigin
import app.subloka.core.domain.TranslationStatus
import kotlin.math.roundToInt

internal fun CaptionProject.toEntity() = ProjectEntity(
    id = id,
    title = title,
    source_uri = sourceUri,
    source_display_name = sourceDisplayName,
    source_size_bytes = sourceSizeBytes,
    source_fingerprint = sourceFingerprint,
    duration_us = durationUs,
    width_px = widthPx,
    height_px = heightPx,
    rotation_degrees = rotationDegrees,
    source_language = sourceLanguage.code.lowercase(),
    target_language = targetLanguage.code.lowercase(),
    content_revision = contentRevision,
    created_at_ms = createdAtMs,
    updated_at_ms = updatedAtMs,
)

internal fun ProjectEntity.toDomain() = CaptionProject(
    id = id,
    title = title,
    sourceUri = source_uri,
    sourceDisplayName = source_display_name,
    sourceSizeBytes = source_size_bytes,
    sourceFingerprint = source_fingerprint,
    durationUs = duration_us,
    widthPx = width_px,
    heightPx = height_px,
    rotationDegrees = rotation_degrees,
    sourceLanguage = sourceLanguageFromCode(source_language),
    targetLanguage = sourceLanguageFromCode(target_language),
    contentRevision = content_revision,
    createdAtMs = created_at_ms,
    updatedAtMs = updated_at_ms,
)

internal fun CaptionSegment.toEntity(projectId: String, updatedAtMs: Long) = CaptionSegmentEntity(
    id = id,
    project_id = projectId,
    start_us = startUs,
    end_us = endUs,
    source_text = sourceText,
    translated_text = translationText.ifBlank { null },
    source_revision = sourceRevision,
    translation_source_revision = translationSourceRevision,
    translation_status = translationStatus.name,
    translation_origin = if (translationText.isBlank()) TranslationOrigin.NONE.name else translationOrigin.name,
    updated_at_ms = updatedAtMs,
)

internal fun CaptionSegmentEntity.toDomain(sourceLanguage: SourceLanguage) = CaptionSegment(
    id = id,
    startUs = start_us,
    endUs = end_us,
    sourceLanguage = sourceLanguage,
    sourceText = source_text,
    translationText = translated_text.orEmpty(),
    translationStatus = TranslationStatus.valueOf(translation_status),
    translationOrigin = TranslationOrigin.valueOf(translation_origin),
    sourceRevision = source_revision,
    translationSourceRevision = translation_source_revision,
)

internal fun CaptionStyle.toEntity(projectId: String) = CaptionStyleEntity(
    project_id = projectId,
    display_mode = displayMode.name,
    source_first = order == CaptionOrder.SOURCE_FIRST,
    font_asset_id = null,
    source_size_ratio = sourceSizePercent / 100f,
    translation_size_ratio = translationSizePercent / 100f,
    source_color_argb = 0xFFFFFFFFL,
    translation_color_argb = 0xFFFFFFFFL,
    outline_color_argb = 0xFF000000L,
    outline_width_ratio = if (outlineEnabled) 0.003f else 0f,
    background_color_argb = 0x99000000L,
    background_enabled = backgroundEnabled,
    anchor_x = 0.5f,
    anchor_y = 1f - (bottomPositionPercent / 100f),
    max_width_ratio = 0.88f,
    line_gap_ratio = 0.02f,
    alignment = "CENTER",
)

internal fun CaptionStyleEntity.toDomain() = CaptionStyle(
    displayMode = CaptionDisplayMode.valueOf(display_mode),
    order = if (source_first) CaptionOrder.SOURCE_FIRST else CaptionOrder.TRANSLATION_FIRST,
    sourceSizePercent = (source_size_ratio * 100).roundToInt(),
    translationSizePercent = (translation_size_ratio * 100).roundToInt(),
    outlineEnabled = outline_width_ratio > 0f,
    backgroundEnabled = background_enabled,
    bottomPositionPercent = ((1f - anchor_y) * 100).roundToInt().coerceIn(0, 100),
)

private fun sourceLanguageFromCode(code: String): SourceLanguage = when (code.lowercase()) {
    "en" -> SourceLanguage.ENGLISH
    "id" -> SourceLanguage.INDONESIA
    else -> error("Unsupported language code: $code")
}
