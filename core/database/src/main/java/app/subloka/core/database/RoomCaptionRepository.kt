package app.subloka.core.database

import androidx.room.withTransaction
import app.subloka.core.domain.CaptionEditingRules
import app.subloka.core.domain.CaptionRepository
import app.subloka.core.domain.CaptionSegment
import app.subloka.core.domain.CaptionTimelineValidator
import app.subloka.core.domain.EditorMutation
import app.subloka.core.domain.SourceLanguage
import app.subloka.core.domain.TranslationOrigin
import app.subloka.core.domain.TranslationStatus
import java.util.UUID

class RoomCaptionRepository(
    private val database: SubLokaDatabase,
    private val idFactory: () -> String = { UUID.randomUUID().toString() },
    private val nowMs: () -> Long = System::currentTimeMillis,
) : CaptionRepository {
    private val projectDao = database.projectDao()
    private val captionDao = database.captionDao()

    override suspend fun list(projectId: String): List<CaptionSegment> {
        val project = requireProject(projectId)
        val language = project.sourceLanguage()
        return captionDao.list(projectId).map { it.toDomain(language) }
    }

    override suspend fun replaceAll(
        projectId: String,
        segments: List<CaptionSegment>,
    ): EditorMutation<List<CaptionSegment>> = database.withTransaction {
        val project = requireProject(projectId)
        validateForProject(project, segments)
        captionDao.deleteForProject(projectId)
        if (segments.isNotEmpty()) {
            val now = nowMs()
            captionDao.insertAll(segments.map { it.toEntity(projectId, now) })
        }
        bumpRevision(projectId)
        EditorMutation(segments.sortedBy { it.startUs }, requireProject(projectId).content_revision)
    }

    override suspend fun saveSourceText(
        projectId: String,
        segmentId: String,
        sourceText: String,
    ): EditorMutation<CaptionSegment> = database.withTransaction {
        val project = requireProject(projectId)
        val current = requireSegment(projectId, segmentId)
        val hasTranslation = !current.translated_text.isNullOrBlank()
        val updated = current.copy(
            source_text = sourceText,
            source_revision = current.source_revision + 1,
            translation_status = if (hasTranslation) TranslationStatus.STALE.name else TranslationStatus.MISSING.name,
            translation_origin = if (hasTranslation) current.translation_origin else TranslationOrigin.NONE.name,
            updated_at_ms = nowMs(),
        )
        check(captionDao.update(updated) == 1) { "Failed to update segment: $segmentId" }
        bumpRevision(projectId)
        EditorMutation(updated.toDomain(project.sourceLanguage()), requireProject(projectId).content_revision)
    }

    override suspend fun saveManualTranslation(
        projectId: String,
        segmentId: String,
        translationText: String,
    ): EditorMutation<CaptionSegment> = database.withTransaction {
        val project = requireProject(projectId)
        val current = requireSegment(projectId, segmentId)
        val blank = translationText.isBlank()
        val updated = current.copy(
            translated_text = translationText.ifBlank { null },
            translation_source_revision = if (blank) null else current.source_revision,
            translation_status = if (blank) TranslationStatus.MISSING.name else TranslationStatus.CURRENT.name,
            translation_origin = if (blank) TranslationOrigin.NONE.name else TranslationOrigin.MANUAL.name,
            updated_at_ms = nowMs(),
        )
        check(captionDao.update(updated) == 1) { "Failed to update segment: $segmentId" }
        bumpRevision(projectId)
        EditorMutation(updated.toDomain(project.sourceLanguage()), requireProject(projectId).content_revision)
    }

    override suspend fun saveTiming(
        projectId: String,
        segmentId: String,
        startUs: Long,
        endUs: Long,
    ): EditorMutation<CaptionSegment> = database.withTransaction {
        val project = requireProject(projectId)
        val language = project.sourceLanguage()
        val entities = captionDao.list(projectId)
        val index = entities.indexOfFirst { it.id == segmentId }
        require(index >= 0) { "Unknown segment: $segmentId" }

        val candidate = entities[index].copy(start_us = startUs, end_us = endUs, updated_at_ms = nowMs())
        val domainSegments = entities.toMutableList().also { it[index] = candidate }.map { it.toDomain(language) }
        validateForProject(project, domainSegments)

        check(captionDao.update(candidate) == 1) { "Failed to update timing: $segmentId" }
        bumpRevision(projectId)
        EditorMutation(candidate.toDomain(language), requireProject(projectId).content_revision)
    }

    override suspend fun splitSegment(
        projectId: String,
        segmentId: String,
        splitUs: Long,
    ): EditorMutation<List<CaptionSegment>> = database.withTransaction {
        val project = requireProject(projectId)
        val language = project.sourceLanguage()
        val current = requireSegment(projectId, segmentId)
        require(splitUs > current.start_us && splitUs < current.end_us) { "splitUs must be inside the segment" }

        val ratio = (splitUs - current.start_us).toDouble() / (current.end_us - current.start_us).toDouble()
        val sourceParts = CaptionEditingRules.splitTextSuggestion(current.source_text, ratio)
        val translationParts = CaptionEditingRules.splitTextSuggestion(current.translated_text.orEmpty(), ratio)
        val hasTranslation = !current.translated_text.isNullOrBlank()
        val status = if (hasTranslation) TranslationStatus.STALE else TranslationStatus.MISSING
        val origin = if (hasTranslation) TranslationOrigin.valueOf(current.translation_origin) else TranslationOrigin.NONE
        val now = nowMs()

        val left = CaptionSegment(
            id = idFactory(),
            startUs = current.start_us,
            endUs = splitUs,
            sourceLanguage = language,
            sourceText = sourceParts.first,
            translationText = translationParts.first,
            translationStatus = status,
            translationOrigin = origin,
            sourceRevision = 1,
            translationSourceRevision = if (hasTranslation) 0 else null,
        )
        val right = CaptionSegment(
            id = idFactory(),
            startUs = splitUs,
            endUs = current.end_us,
            sourceLanguage = language,
            sourceText = sourceParts.second,
            translationText = translationParts.second,
            translationStatus = status,
            translationOrigin = origin,
            sourceRevision = 1,
            translationSourceRevision = if (hasTranslation) 0 else null,
        )

        val replacement = captionDao.list(projectId)
            .filterNot { it.id == segmentId }
            .map { it.toDomain(language) } + listOf(left, right)
        validateForProject(project, replacement)

        captionDao.deleteByIds(projectId, listOf(segmentId))
        captionDao.insertAll(listOf(left.toEntity(projectId, now), right.toEntity(projectId, now)))
        bumpRevision(projectId)

        EditorMutation(listOf(left, right), requireProject(projectId).content_revision)
    }

    override suspend fun mergeWithNext(
        projectId: String,
        segmentId: String,
    ): EditorMutation<CaptionSegment> = database.withTransaction {
        val project = requireProject(projectId)
        val language = project.sourceLanguage()
        val ordered = captionDao.list(projectId)
        val index = ordered.indexOfFirst { it.id == segmentId }
        require(index >= 0) { "Unknown segment: $segmentId" }
        require(index < ordered.lastIndex) { "Segment has no next segment to merge" }

        val first = ordered[index]
        val second = ordered[index + 1]
        val mergedTranslation = CaptionEditingRules.mergeText(
            first.translated_text.orEmpty(),
            second.translated_text.orEmpty(),
        )
        val hasTranslation = mergedTranslation.isNotBlank()
        val mergedOrigin = when {
            !hasTranslation -> TranslationOrigin.NONE
            first.translation_origin == TranslationOrigin.MANUAL.name ||
                second.translation_origin == TranslationOrigin.MANUAL.name -> TranslationOrigin.MANUAL
            else -> TranslationOrigin.MACHINE
        }

        val merged = CaptionSegment(
            id = idFactory(),
            startUs = first.start_us,
            endUs = second.end_us,
            sourceLanguage = language,
            sourceText = CaptionEditingRules.mergeText(first.source_text, second.source_text),
            translationText = mergedTranslation,
            translationStatus = if (hasTranslation) TranslationStatus.STALE else TranslationStatus.MISSING,
            translationOrigin = mergedOrigin,
            sourceRevision = 1,
            translationSourceRevision = if (hasTranslation) 0 else null,
        )

        val replacement = ordered
            .filterNot { it.id == first.id || it.id == second.id }
            .map { it.toDomain(language) } + merged
        validateForProject(project, replacement)

        captionDao.deleteByIds(projectId, listOf(first.id, second.id))
        captionDao.insertAll(listOf(merged.toEntity(projectId, nowMs())))
        bumpRevision(projectId)

        EditorMutation(merged, requireProject(projectId).content_revision)
    }

    override suspend fun restoreSnapshot(
        projectId: String,
        segments: List<CaptionSegment>,
    ): EditorMutation<List<CaptionSegment>> = replaceAll(projectId, segments)

    override suspend fun applyMachineTranslation(
        projectId: String,
        segmentId: String,
        expectedSourceRevision: Long,
        translationText: String,
        allowReplaceManual: Boolean,
    ): EditorMutation<CaptionSegment>? = database.withTransaction {
        require(translationText.isNotBlank()) { "Machine translation must not be blank" }
        val project = requireProject(projectId)
        val updated = captionDao.applyMachineTranslation(
            projectId = projectId,
            segmentId = segmentId,
            expectedSourceRevision = expectedSourceRevision,
            translationText = translationText,
            updatedAtMs = nowMs(),
            allowReplaceManual = if (allowReplaceManual) 1 else 0,
        )
        if (updated == 0) {
            null
        } else {
            bumpRevision(projectId)
            val segment = requireSegment(projectId, segmentId).toDomain(project.sourceLanguage())
            EditorMutation(segment, requireProject(projectId).content_revision)
        }
    }

    private suspend fun bumpRevision(projectId: String) {
        check(projectDao.bumpRevision(projectId, nowMs()) == 1) { "Failed to update project revision" }
    }

    private suspend fun requireProject(projectId: String): ProjectEntity =
        requireNotNull(projectDao.find(projectId)) { "Unknown project: $projectId" }

    private suspend fun requireSegment(projectId: String, segmentId: String): CaptionSegmentEntity =
        requireNotNull(captionDao.find(projectId, segmentId)) { "Unknown segment: $segmentId" }

    private fun validateForProject(project: ProjectEntity, segments: List<CaptionSegment>) {
        val language = project.sourceLanguage()
        require(segments.all { it.sourceLanguage == language }) { "Segment source language differs from project" }
        CaptionTimelineValidator.validate(project.duration_us, segments)
    }

    private fun ProjectEntity.sourceLanguage(): SourceLanguage = when (source_language.lowercase()) {
        "en" -> SourceLanguage.ENGLISH
        "id" -> SourceLanguage.INDONESIA
        else -> error("Unsupported project source language: $source_language")
    }
}
