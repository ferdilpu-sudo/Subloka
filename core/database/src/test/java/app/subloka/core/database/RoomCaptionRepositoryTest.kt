package app.subloka.core.database

import android.content.Context
import androidx.room.Room
import androidx.room.withTransaction
import androidx.test.core.app.ApplicationProvider
import app.subloka.core.domain.CaptionProject
import app.subloka.core.domain.CaptionSegment
import app.subloka.core.domain.CaptionStyle
import app.subloka.core.domain.SourceLanguage
import app.subloka.core.domain.TranslationOrigin
import app.subloka.core.domain.TranslationStatus
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class RoomCaptionRepositoryTest {
    private val context: Context = ApplicationProvider.getApplicationContext()
    private val databaseName = "subloka-t08-test.db"
    private lateinit var database: SubLokaDatabase
    private lateinit var projectRepository: RoomProjectRepository
    private lateinit var captionRepository: RoomCaptionRepository

    private var nextId = 0
    private var clock = 10_000L

    @Before
    fun setUp() {
        context.deleteDatabase(databaseName)
        openDatabase()
    }

    @After
    fun tearDown() {
        database.close()
        context.deleteDatabase(databaseName)
    }

    @Test
    fun sourceEditBecomesStaleIncrementsRevisionAndSurvivesReopen() = runBlocking {
        seedProjectAndSegments()

        val mutation = captionRepository.saveSourceText(PROJECT_ID, "segment-1", "Edited source")
        assertEquals(2L, mutation.value.sourceRevision)
        assertEquals(TranslationStatus.STALE, mutation.value.translationStatus)
        assertEquals(1L, mutation.value.translationSourceRevision)
        assertEquals(2L, mutation.contentRevision)

        database.close()
        openDatabase()

        val persisted = captionRepository.list(PROJECT_ID).first { it.id == "segment-1" }
        assertEquals("Edited source", persisted.sourceText)
        assertEquals(TranslationStatus.STALE, persisted.translationStatus)
        assertEquals(2L, projectRepository.find(PROJECT_ID)?.contentRevision)
    }

    @Test
    fun timingRejectsOverlapWithoutMutatingStoredSegment() = runBlocking {
        seedProjectAndSegments()

        assertThrows(IllegalArgumentException::class.java) {
            runBlocking {
                captionRepository.saveTiming(PROJECT_ID, "segment-2", 900_000, 2_500_000)
            }
        }

        val unchanged = captionRepository.list(PROJECT_ID).first { it.id == "segment-2" }
        assertEquals(1_000_000L, unchanged.startUs)
        assertEquals(2_000_000L, unchanged.endUs)
    }

    @Test
    fun splitAndMergeCreateNewStableIdsAndMarkTranslationStale() = runBlocking {
        seedProjectAndSegments()

        val split = captionRepository.splitSegment(PROJECT_ID, "segment-1", 500_000)
        assertEquals(2, split.value.size)
        assertTrue(split.value.all { it.id.startsWith("generated-") })
        assertTrue(split.value.all { it.translationStatus == TranslationStatus.STALE })

        val ordered = captionRepository.list(PROJECT_ID)
        val left = ordered.first { it.startUs == 0L }
        val merged = captionRepository.mergeWithNext(PROJECT_ID, left.id)

        assertTrue(merged.value.id.startsWith("generated-"))
        assertEquals(0L, merged.value.startUs)
        assertEquals(1_000_000L, merged.value.endUs)
        assertEquals(TranslationStatus.STALE, merged.value.translationStatus)
    }

    @Test
    fun machineTranslationUsesCompareAndSetAndProtectsManualEdits() = runBlocking {
        seedProjectAndSegments()
        captionRepository.saveManualTranslation(PROJECT_ID, "segment-1", "Koreksi manual")

        val blockedManual = captionRepository.applyMachineTranslation(
            PROJECT_ID,
            "segment-1",
            expectedSourceRevision = 1,
            translationText = "Mesin",
        )
        assertEquals(null, blockedManual)

        val edited = captionRepository.saveSourceText(PROJECT_ID, "segment-1", "New source")
        assertEquals(2L, edited.value.sourceRevision)

        val staleRevision = captionRepository.applyMachineTranslation(
            PROJECT_ID,
            "segment-1",
            expectedSourceRevision = 1,
            translationText = "Old machine result",
            allowReplaceManual = true,
        )
        assertEquals(null, staleRevision)

        val explicitReplacement = captionRepository.applyMachineTranslation(
            PROJECT_ID,
            "segment-1",
            expectedSourceRevision = 2,
            translationText = "Hasil baru",
            allowReplaceManual = true,
        )
        assertNotNull(explicitReplacement)
        assertEquals(TranslationStatus.CURRENT, explicitReplacement?.value?.translationStatus)
        assertEquals(TranslationOrigin.MACHINE, explicitReplacement?.value?.translationOrigin)
        assertEquals(2L, explicitReplacement?.value?.translationSourceRevision)
    }

    @Test
    fun restoreSnapshotKeepsProjectRevisionMonotonic() = runBlocking {
        seedProjectAndSegments()
        val snapshot = captionRepository.list(PROJECT_ID)

        val edited = captionRepository.saveSourceText(PROJECT_ID, "segment-1", "Temporary edit")
        assertEquals(2L, edited.contentRevision)

        val restored = captionRepository.restoreSnapshot(PROJECT_ID, snapshot)
        assertEquals(3L, restored.contentRevision)
        assertEquals("This place is beautiful", restored.value.first { it.id == "segment-1" }.sourceText)
        assertEquals(3L, projectRepository.find(PROJECT_ID)?.contentRevision)
    }

    @Test
    fun styleAutosavePersistsAndBumpsProjectRevision() = runBlocking {
        seedProjectAndSegments()
        val style = CaptionStyle(
            sourceSizePercent = 110,
            translationSizePercent = 96,
            outlineEnabled = false,
            backgroundEnabled = true,
            bottomPositionPercent = 18,
        )

        val mutation = projectRepository.saveStyle(PROJECT_ID, style)
        assertEquals(2L, mutation.contentRevision)

        database.close()
        openDatabase()
        assertEquals(style, projectRepository.getStyle(PROJECT_ID))
    }

    @Test
    fun generatedPublicationRequiresEmptyProjectAndExactRevisionAndSurvivesReopen() = runBlocking {
        projectRepository.upsert(project())
        val generated = listOf(CaptionSegment("asr-1", 0, 1_000_000, SourceLanguage.ENGLISH, "Generated", "", TranslationStatus.MISSING, TranslationOrigin.NONE))
        assertFalse(captionRepository.publishGenerated(PROJECT_ID, 7, generated))
        assertTrue(captionRepository.list(PROJECT_ID).isEmpty())
        assertTrue(captionRepository.publishGenerated(PROJECT_ID, 0, generated))
        assertFalse(captionRepository.publishGenerated(PROJECT_ID, 1, generated.map { it.copy(sourceText = "overwrite") }))
        database.close()
        openDatabase()
        assertEquals("Generated", captionRepository.list(PROJECT_ID).single().sourceText)
        assertEquals(1L, projectRepository.find(PROJECT_ID)?.contentRevision)
    }

    @Test
    fun invalidGeneratedTimelineRollsBackWithoutBumpingRevision() = runBlocking {
        projectRepository.upsert(project())
        assertThrows(IllegalArgumentException::class.java) {
            runBlocking { captionRepository.publishGenerated(PROJECT_ID, 0,
                listOf(currentSegment("bad", 0, 11_000_000, "Outside video", "Translation"))) }
        }
        assertEquals(0L, projectRepository.find(PROJECT_ID)?.contentRevision)
        assertTrue(captionRepository.list(PROJECT_ID).isEmpty())
    }

    @Test
    fun translationCasRejectsDeletedSegmentAndSuccessfulTranslationSurvivesReopen() = runBlocking {
        seedProjectAndSegments()
        val snapshot = captionRepository.list(PROJECT_ID).first()
        assertNotNull(captionRepository.applyMachineTranslation(PROJECT_ID, snapshot.id, snapshot.sourceRevision, "Generated result"))
        database.close()
        openDatabase()
        val saved = captionRepository.list(PROJECT_ID).first()
        assertEquals("Generated result", saved.translationText)
        assertEquals(saved.sourceRevision, saved.translationSourceRevision)
        captionRepository.splitSegment(PROJECT_ID, snapshot.id, 500_000)
        assertEquals(null, captionRepository.applyMachineTranslation(PROJECT_ID, snapshot.id, snapshot.sourceRevision, "Late deleted result"))
        assertFalse(captionRepository.list(PROJECT_ID).any { it.translationText == "Late deleted result" })
    }

    @Test
    fun interruptedReplacementResumesOnlyUncommittedCaptionAfterDatabaseReopen() = runBlocking {
        seedProjectAndSegments()
        val store = TranslationRecoveryStore(database)
        val snapshot = captionRepository.list(PROJECT_ID)
        val first = store.begin(PROJECT_ID, "gemma:test", snapshot)
        assertTrue(store.publish(first.id, snapshot[0], "Improved first"))
        // Simulate death with a persisted RUNNING job, without graceful stop.
        database.close(); openDatabase()
        val reopened = TranslationRecoveryStore(database)
        reopened.recoverInterrupted()
        val pending = requireNotNull(reopened.pending(PROJECT_ID))
        assertEquals(mapOf("segment-2" to 1L), pending.pending)
        assertEquals("INTERRUPTED", database.processingJobDao().find(first.id)?.state)
        val attempt = reopened.begin(PROJECT_ID, "gemma:test", captionRepository.list(PROJECT_ID), pending.id)
        assertEquals(setOf("segment-2"), attempt.pending.keys)
        assertEquals("CANCELLED", database.processingJobDao().find(first.id)?.state)
        assertTrue(reopened.publish(attempt.id, snapshot[1], "Improved second"))
        assertEquals(null, reopened.pending(PROJECT_ID))
        assertEquals(listOf("Improved first", "Improved second"), captionRepository.list(PROJECT_ID).map { it.translationText })
        assertEquals(snapshot.map { it.startUs to it.endUs }, captionRepository.list(PROJECT_ID).map { it.startUs to it.endUs })
    }

    @Test
    fun recoveryResultAndCheckpointRollbackTogether() = runBlocking {
        seedProjectAndSegments()
        val store = TranslationRecoveryStore(database)
        val snapshot = captionRepository.list(PROJECT_ID)
        val job = store.begin(PROJECT_ID, "gemma:test", snapshot)
        try {
            database.withTransaction {
                store.publish(job.id, snapshot[0], "Must roll back")
                error("injected interruption before transaction commit")
            }
        } catch (_: IllegalStateException) { }
        assertEquals(snapshot, captionRepository.list(PROJECT_ID))
        assertEquals(job.pending, store.pending(PROJECT_ID)?.pending)
        store.stop(job.id, interrupted = true)
        assertEquals("INTERRUPTED", database.processingJobDao().find(job.id)?.state)
    }

    @Test
    fun resumeRejectsEngineChangeAndPrunesManualOrChangedSources() = runBlocking {
        seedProjectAndSegments()
        val store = TranslationRecoveryStore(database)
        val snapshot = captionRepository.list(PROJECT_ID)
        val job = store.begin(PROJECT_ID, "gemma:test", snapshot)
        store.stop(job.id, interrupted = false)
        assertEquals("FAILED", database.processingJobDao().find(job.id)?.state)
        try { store.begin(PROJECT_ID, "mlkit:test", snapshot, job.id); fail("Engine must remain bound") }
        catch (_: IllegalStateException) { }
        captionRepository.saveManualTranslation(PROJECT_ID, "segment-1", "Manual correction")
        captionRepository.saveSourceText(PROJECT_ID, "segment-2", "Changed source")
        val current = captionRepository.list(PROJECT_ID)
        val resumed = store.begin(PROJECT_ID, "gemma:test", current, job.id)
        assertTrue(resumed.pending.isEmpty())
        assertEquals(current, captionRepository.list(PROJECT_ID))
        assertEquals(null, store.pending(PROJECT_ID))
    }

    @Test
    fun lateManualEditIsProtectedAndDiscardKeepsPublishedCaption() = runBlocking {
        seedProjectAndSegments()
        val store = TranslationRecoveryStore(database)
        val snapshot = captionRepository.list(PROJECT_ID)
        val job = store.begin(PROJECT_ID, "gemma:test", snapshot)
        captionRepository.saveManualTranslation(PROJECT_ID, "segment-1", "Manual wins")
        assertFalse(store.publish(job.id, snapshot[0], "Late machine output"))
        assertEquals(setOf("segment-2"), store.pending(PROJECT_ID)?.pending?.keys)
        store.discard(PROJECT_ID)
        assertEquals(null, store.pending(PROJECT_ID))
        assertEquals("Manual wins", captionRepository.list(PROJECT_ID)[0].translationText)
        assertEquals(snapshot[1].translationText, captionRepository.list(PROJECT_ID)[1].translationText)
    }

    private suspend fun seedProjectAndSegments() {
        projectRepository.upsert(project())
        val mutation = captionRepository.replaceAll(
            PROJECT_ID,
            listOf(
                currentSegment(
                    id = "segment-1",
                    startUs = 0,
                    endUs = 1_000_000,
                    source = "This place is beautiful",
                    translation = "Tempat ini indah",
                ),
                currentSegment(
                    id = "segment-2",
                    startUs = 1_000_000,
                    endUs = 2_000_000,
                    source = "Keep walking",
                    translation = "Lanjut berjalan",
                ),
            ),
        )
        assertEquals(1L, mutation.contentRevision)
    }

    @Test
    fun relinkPreservesManualCaptionsStyleAndCheckpointAcrossReopen() = runBlocking {
        seedProjectAndSegments()
        val original = requireNotNull(projectRepository.find(PROJECT_ID)).copy(sourceFingerprint = "a".repeat(64))
        projectRepository.upsert(original)
        captionRepository.saveSourceText(PROJECT_ID, "segment-1", "Manual source")
        captionRepository.saveManualTranslation(PROJECT_ID, "segment-1", "Terjemahan manual")
        val style = CaptionStyle()
        projectRepository.saveStyle(PROJECT_ID, style)
        val before = requireNotNull(projectRepository.find(PROJECT_ID))
        val captions = captionRepository.list(PROJECT_ID)
        val recovery = TranslationRecoveryStore(database)
        val checkpoint = recovery.begin(PROJECT_ID, "gemma:test", captions)
        recovery.stop(checkpoint.id, true)
        val pending = recovery.pending(PROJECT_ID)
        val candidate = relinkCandidate(before)

        val result = projectRepository.relinkSource(PROJECT_ID, before.sourceUri, before.sourceFingerprint, candidate)
        assertNotNull(result)
        assertEquals(before.contentRevision, result!!.contentRevision)
        assertEquals(before.title, result.title)
        database.close()
        openDatabase()
        assertEquals(candidate.uri, projectRepository.find(PROJECT_ID)!!.sourceUri)
        assertEquals(captions, captionRepository.list(PROJECT_ID))
        assertEquals(style, projectRepository.getStyle(PROJECT_ID))
        assertEquals(pending, TranslationRecoveryStore(database).pending(PROJECT_ID))
    }

    @Test
    fun relinkRejectsChangedFileMetadataMissingFingerprintAndStaleSource() = runBlocking {
        seedProjectAndSegments()
        val original = requireNotNull(projectRepository.find(PROJECT_ID)).copy(sourceFingerprint = "a".repeat(64))
        projectRepository.upsert(original)
        val captions = captionRepository.list(PROJECT_ID)
        val candidate = relinkCandidate(original)
        for (bad in listOf(candidate.copy(fingerprintSha256 = "b".repeat(64)),
            candidate.copy(durationUs = candidate.durationUs + 1),
            candidate.copy(widthPx = candidate.widthPx + 1),
            candidate.copy(rotationDegrees = 90), candidate.copy(sizeBytes = 999))) {
            assertEquals(null, projectRepository.relinkSource(PROJECT_ID, original.sourceUri, original.sourceFingerprint, bad))
            assertEquals(original, projectRepository.find(PROJECT_ID))
        }
        assertEquals(null, projectRepository.relinkSource(PROJECT_ID, "content://stale", original.sourceFingerprint, candidate))
        projectRepository.upsert(original.copy(sourceFingerprint = null))
        assertEquals(null, projectRepository.relinkSource(PROJECT_ID, original.sourceUri, null, candidate))
        assertEquals(captions, captionRepository.list(PROJECT_ID))
    }

    private fun relinkCandidate(project: CaptionProject) = app.subloka.core.domain.MediaDescriptor(
        uri = "content://replacement/original.mp4", displayName = "original-copy.mp4",
        sizeBytes = project.sourceSizeBytes, fingerprintSha256 = requireNotNull(project.sourceFingerprint),
        durationUs = project.durationUs, widthPx = project.widthPx, heightPx = project.heightPx,
        rotationDegrees = project.rotationDegrees,
        audioTracks = listOf(app.subloka.core.domain.AudioTrackDescriptor(1, "audio/mp4a-latm", 48000, 2, null)))

    private fun openDatabase() {
        database = Room.databaseBuilder(context, SubLokaDatabase::class.java, databaseName)
            .allowMainThreadQueries()
            .build()
        projectRepository = RoomProjectRepository(database) { ++clock }
        captionRepository = RoomCaptionRepository(
            database = database,
            idFactory = { "generated-${++nextId}" },
            nowMs = { ++clock },
        )
    }

    private fun project() = CaptionProject(
        id = PROJECT_ID,
        title = "Traveling",
        sourceUri = "content://subloka/traveling.mp4",
        sourceDisplayName = "Traveling.mp4",
        sourceSizeBytes = 1_024L,
        sourceFingerprint = "fixture",
        durationUs = 10_000_000,
        widthPx = 1_920,
        heightPx = 1_080,
        rotationDegrees = 0,
        sourceLanguage = SourceLanguage.ENGLISH,
        targetLanguage = SourceLanguage.INDONESIA,
        contentRevision = 0,
        createdAtMs = 1_000,
        updatedAtMs = 1_000,
    )

    private fun currentSegment(
        id: String,
        startUs: Long,
        endUs: Long,
        source: String,
        translation: String,
    ) = CaptionSegment(
        id = id,
        startUs = startUs,
        endUs = endUs,
        sourceLanguage = SourceLanguage.ENGLISH,
        sourceText = source,
        translationText = translation,
        translationStatus = TranslationStatus.CURRENT,
        translationOrigin = TranslationOrigin.MACHINE,
        sourceRevision = 1,
        translationSourceRevision = 1,
    )

    companion object {
        private const val PROJECT_ID = "project-1"
    }
}
