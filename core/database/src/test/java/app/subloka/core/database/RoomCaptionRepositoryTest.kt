package app.subloka.core.database

import android.content.Context
import androidx.room.Room
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
