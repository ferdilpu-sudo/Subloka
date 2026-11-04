package app.subloka

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import app.subloka.core.domain.*
import app.subloka.feature.editor.EditorScreen
import app.subloka.feature.editor.VideoPreview
import app.subloka.feature.editor.StyleWorkspace
import app.subloka.feature.editor.TimingWorkspace
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import org.junit.Rule
import org.junit.Test
import org.junit.Assert.assertTrue
import kotlinx.coroutines.*

class EditorLayoutTest {
    @get:Rule val compose = createComposeRule()

    @Test fun legacyExampleDoesNotGenerateSimulatedTranslation() {
        val caption = CaptionSegment("example", 0, 2_000_000, SourceLanguage.INDONESIA,
            "Contoh kalimat", "", TranslationStatus.MISSING)
        compose.setContent {
            MaterialTheme {
                EditorScreen(listOf(caption), CaptionStyle(), null, "Tersimpan", false,
                    {}, {}, {}, {}, demoMode = true)
            }
        }
        compose.onNodeWithText("Buka terjemahan", substring = true).performScrollTo().performClick()
        compose.onNodeWithText("Terjemahan tidak tersedia pada contoh").performScrollTo().assertIsNotEnabled()
    }

    @Test fun platformErrorsDoNotExposePrivatePaths() {
        val fallback = "Pilih video lain dan coba lagi."
        assertTrue(UiFailureMessage.describe(IllegalStateException("/private/video.mp4 native error"), fallback) == fallback)
        assertTrue(UiFailureMessage.describe(android.database.sqlite.SQLiteFullException(), fallback).contains("Penyimpanan penuh"))
        assertTrue(UiFailureMessage.describe(MediaSourceException(MediaErrorCode.NO_AUDIO, "native details"), fallback).contains("tidak memiliki audio"))
        val relink = "Video berbeda dari sumber asli. Pilih file asli yang sama; caption tidak diubah."
        assertTrue(UiFailureMessage.describe(IllegalStateException(relink), fallback) == relink)
    }

    @Test fun repeatedNavigationFlushDoesNotAcknowledgeWriteFailure() = runBlocking {
        val store = androidx.lifecycle.ViewModelStore()
        try {
            val model = withContext(Dispatchers.Main) {
                val app = androidx.test.platform.app.InstrumentationRegistry.getInstrumentation()
                    .targetContext.applicationContext as android.app.Application
                androidx.lifecycle.ViewModelProvider(store,
                    androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory(app))[SubLokaViewModel::class.java]
            }
            suspend fun flush(): Boolean {
                val result = CompletableDeferred<Boolean>()
                withContext(Dispatchers.Main) { model.flush { result.complete(it) } }
                return withTimeout(10_000) { result.await() }
            }
            assertTrue(flush())
            // Inject a failed write without damaging the device database.
            withContext(Dispatchers.Main) {
                SubLokaViewModel::class.java.getDeclaredField("writeFailed").apply {
                    isAccessible = true
                    setBoolean(model, true)
                }
            }
            assertTrue(!flush())
            assertTrue(!flush())
        } finally { withContext(Dispatchers.Main) { store.clear() } }
    }

    @Test fun failedSaveRetriesCurrentCorrectionAndBlocksExport() {
        val caption = CaptionSegment("retry", 0, 2_000_000, SourceLanguage.INDONESIA,
            "Sebelum koreksi", "", TranslationStatus.MISSING)
        var retried: List<CaptionSegment>? = null
        compose.setContent {
            MaterialTheme {
                EditorScreen(listOf(caption), CaptionStyle(), null, "Perubahan belum tersimpan", true,
                    {}, {}, {}, {}, demoMode = false,
                    onRetrySave = { segments, _ -> retried = segments })
            }
        }
        compose.onNodeWithText("Ekspor").assertIsNotEnabled()
        compose.onNodeWithText("Teks asli").performScrollTo().performTextReplacement("Koreksi terbaru")
        compose.onNodeWithText("Coba simpan lagi").performClick()
        compose.runOnIdle { assertTrue(retried?.single()?.sourceText == "Koreksi terbaru") }
    }

    @Test fun shortLandscapeShowsPreviewAlongsideReachableCaptionAndTools() {
        var exported = false
        val caption = CaptionSegment("landscape", 0, 2_000_000, SourceLanguage.INDONESIA,
            "Caption landscape", "", TranslationStatus.MISSING)
        compose.setContent {
            val density = LocalDensity.current
            // Fit a landscape-sized layout inside the portrait test host without clipping.
            CompositionLocalProvider(LocalDensity provides Density(density.density * 0.5f, 1f)) {
                MaterialTheme {
                    Box(Modifier.size(640.dp, 320.dp)) {
                        EditorScreen(listOf(caption), CaptionStyle(), null, "Tersimpan", false,
                            {}, {}, {}, { exported = true }, demoMode = false)
                    }
                }
            }
        }
        compose.onNodeWithText("Pratinjau video belum tersedia").assertIsDisplayed()
        compose.onNodeWithText("Teks asli").performScrollTo().assertIsDisplayed()
        val preview = compose.onNodeWithText("Pratinjau video belum tersedia").fetchSemanticsNode().boundsInRoot
        val field = compose.onNodeWithText("Teks asli").fetchSemanticsNode().boundsInRoot
        assertTrue("Landscape video and caption must be side by side", preview.right <= field.left)
        compose.onNodeWithText("Waktu").performScrollTo().performClick()
        compose.onNodeWithText("Perubahan berhenti", substring = true).performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Gaya").performClick()
        compose.onNodeWithText("Pratinjau dan MP4", substring = true).performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Pratinjau video belum tersedia").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Ekspor").assertIsDisplayed().performClick()
        compose.runOnIdle { assertTrue(exported) }
    }

    @Test fun correctionNavigationPreservesEditsAndProtectsBoundaryActions() {
        val first = CaptionSegment("first", 0, 2_000_000, SourceLanguage.INDONESIA,
            "Kalimat pertama", "First sentence", TranslationStatus.CURRENT)
        val second = first.copy(id = "second", startUs = 2_000_000, endUs = 4_000_000,
            sourceText = "Kalimat kedua")
        var saved = listOf(first, second)
        compose.setContent {
            MaterialTheme {
                Box(Modifier.size(360.dp, 640.dp)) {
                    EditorScreen(saved, CaptionStyle(), null, "Tersimpan", false,
                        { saved = it }, {}, {}, {}, demoMode = false)
                }
            }
        }
        compose.onNodeWithContentDescription("Caption sebelumnya").assertIsNotEnabled()
        compose.onNodeWithText("Teks asli").performScrollTo().performTextReplacement("Koreksi pertama")
        compose.onNodeWithContentDescription("Caption berikutnya").performClick()
        compose.onNodeWithText("Caption 2 dari 2").assertIsDisplayed()
        compose.onNodeWithContentDescription("Caption berikutnya").assertIsNotEnabled()
        compose.onNodeWithText("Gabung berikutnya").performScrollTo().assertIsNotEnabled()
        compose.onNodeWithContentDescription("Caption sebelumnya").performClick()
        compose.onNodeWithText("Teks asli").performScrollTo().assertTextContains("Koreksi pertama")
        compose.runOnIdle {
            assertTrue(saved.first().sourceText == "Koreksi pertama")
            assertTrue(saved.first().translationText == "First sentence")
            assertTrue(saved.first().translationStatus == TranslationStatus.STALE)
        }
        compose.onNodeWithText("! Perlu diperbarui").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Buka terjemahan", substring = true).performScrollTo().performClick()
        compose.onNodeWithText("Terjemahan", substring = false).performScrollTo().assertTextContains("First sentence")
        compose.onNodeWithText("Waktu").performClick()
        compose.onAllNodesWithText("-10 ms")[0].performScrollTo().assertIsNotEnabled()
        compose.onAllNodesWithText("+10 ms")[1].performScrollTo().assertIsNotEnabled()
    }

    @Test fun compactPortraitEditSecondCaptionThenThirdWithoutScrollingNavigation() {
        val captions = (1..4).map { index ->
            CaptionSegment("routine-$index", (index - 1L) * 2_000_000L,
                index * 2_000_000L, SourceLanguage.INDONESIA,
                "Kalimat nomor $index", "", TranslationStatus.MISSING)
        }
        var saved = captions
        compose.setContent {
            MaterialTheme {
                Box(Modifier.size(360.dp, 820.dp)) {
                    EditorScreen(
                        captions, CaptionStyle(), null, "Tersimpan lokal", false,
                        { saved = it }, {}, {}, {}, demoMode = false,
                        videoWidth = 1080, videoHeight = 1920,
                    )
                }
            }
        }
        compose.onNodeWithText("Periksa teks, waktu, dan terjemahan sebelum ekspor.")
            .assertDoesNotExist()
        compose.onNodeWithContentDescription("Caption berikutnya").assertIsDisplayed().performClick()
        compose.onNodeWithText("Caption 2 dari 4").assertIsDisplayed()
        val nav = compose.onNodeWithText("Caption 2 dari 4").fetchSemanticsNode().boundsInRoot
        val input = compose.onNodeWithText("Teks asli").fetchSemanticsNode().boundsInRoot
        assertTrue("Caption navigation must be immediately above correction panel", nav.bottom < input.top)
        compose.onNodeWithText("Teks asli").performScrollTo()
            .performTextReplacement("Kalimat nomor dua dikoreksi")
        compose.onNodeWithContentDescription("Caption berikutnya").assertIsDisplayed().performClick()
        compose.onNodeWithText("Caption 3 dari 4").assertIsDisplayed()
        compose.onNodeWithText("Teks asli").performScrollTo().assertTextContains("Kalimat nomor 3")
        compose.runOnIdle {
            assertTrue(saved[1].sourceText == "Kalimat nomor dua dikoreksi")
            assertTrue(saved[2].sourceText == "Kalimat nomor 3")
        }
        compose.onNodeWithText("Waktu").performClick()
        compose.onNodeWithText("Caption 3 dari 4").assertIsDisplayed()
        val timingNav = compose.onNodeWithText("Caption 3 dari 4").fetchSemanticsNode().boundsInRoot
        val timingAction = compose.onNodeWithText("Awal: 00:04.00")
            .performScrollTo().fetchSemanticsNode().boundsInRoot
        assertTrue("Timing navigation must stay above selected timing controls",
            timingNav.bottom < timingAction.top)
        compose.onNodeWithContentDescription("Caption sebelumnya").assertIsDisplayed().performClick()
        compose.onNodeWithText("Caption 2 dari 4").assertIsDisplayed()
        compose.onNodeWithText("Awal: 00:02.00").performScrollTo().assertIsDisplayed()
    }

    @Test fun compactPreviewCanZoomAndStyleStartsWithLargePreview() {
        val caption = CaptionSegment("zoom", 0L, 3_000_000L,
            SourceLanguage.INDONESIA, "Kalimat untuk pratinjau",
            "", TranslationStatus.MISSING)
        compose.setContent {
            MaterialTheme {
                Box(Modifier.size(360.dp, 820.dp)) {
                    EditorScreen(listOf(caption), CaptionStyle(), null,
                        "Tersimpan lokal", false, {}, {}, {}, {},
                        demoMode = false, videoWidth = 1080, videoHeight = 1920)
                }
            }
        }
        val compact = compose.onNodeWithTag("video-preview-frame")
            .fetchSemanticsNode().boundsInRoot
        compose.onNodeWithContentDescription("Perbesar pratinjau").assertIsDisplayed().performClick()
        val expanded = compose.onNodeWithTag("video-preview-frame")
            .fetchSemanticsNode().boundsInRoot
        assertTrue("Zoom must increase the useful portrait preview height",
            expanded.height > compact.height * 1.4f)
        compose.onNodeWithContentDescription("Ringkas pratinjau").performClick()
        val againCompact = compose.onNodeWithTag("video-preview-frame")
            .fetchSemanticsNode().boundsInRoot
        assertTrue("Preview should return to its editing size",
            kotlin.math.abs(againCompact.height - compact.height) <= 2f)
        compose.onNodeWithText("Gaya").performClick()
        val stylePreview = compose.onNodeWithTag("video-preview-frame")
            .fetchSemanticsNode().boundsInRoot
        assertTrue("Style should present a large preview by default",
            stylePreview.height > compact.height * 1.4f)
        compose.onNodeWithContentDescription("Perbesar pratinjau").assertDoesNotExist()
        compose.onNodeWithText("Jarak dari bawah", substring = true)
            .performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Ekspor").assertIsDisplayed()
    }

    @Test fun translationModelActionMovesBelowActiveCaptionEditor() {
        val caption = CaptionSegment("translation", 0L, 2_000_000L,
            SourceLanguage.INDONESIA, "Teks asli singkat",
            "", TranslationStatus.MISSING)
        var requested = 0
        compose.setContent {
            MaterialTheme {
                Box(Modifier.size(360.dp, 760.dp)) {
                    EditorScreen(listOf(caption), CaptionStyle(), null,
                        "Tersimpan lokal", false, {}, {}, {}, {},
                        demoMode = false,
                        onRequestTranslation = { if (it == null) requested++ },
                        videoWidth = 1080, videoHeight = 1920)
                }
            }
        }
        val input = compose.onNodeWithText("Teks asli").fetchSemanticsNode().boundsInRoot
        val action = compose.onNodeWithText("Model / lanjutkan terjemahan")
            .performScrollTo().fetchSemanticsNode().boundsInRoot
        assertTrue("Model management must come after editing controls", input.top < action.top)
        compose.onNodeWithText("Model / lanjutkan terjemahan").performClick()
        compose.runOnIdle { assertTrue(requested == 1) }
    }

    @Test fun captionListRetainsPositionAfterSelectingAndCorrecting() {
        val captions = (1..40).map { index ->
            CaptionSegment("caption-$index", (index - 1) * 2_000_000L, index * 2_000_000L,
                SourceLanguage.INDONESIA, "Kalimat nomor $index", "", TranslationStatus.MISSING)
        }
        compose.setContent {
            MaterialTheme {
                Box(Modifier.size(360.dp, 480.dp)) {
                    EditorScreen(captions, CaptionStyle(), null, "Tersimpan", false,
                        {}, {}, {}, {}, demoMode = false)
                }
            }
        }
        compose.onNodeWithText("Daftar caption (40)").performClick()
        compose.onNodeWithTag("caption-list").performScrollToIndex(25)
        compose.onNodeWithText("Kalimat nomor 26").performClick()
        compose.onNodeWithText("Teks asli").performScrollTo().assertTextContains("Kalimat nomor 26")
        compose.onNodeWithText("Daftar caption (40)").performClick()
        compose.onNodeWithText("Kalimat nomor 26").assertIsDisplayed()
    }

    @Test fun fixedCaptionNavigationReturnsToCorrectionWhenListWasOpen() {
        val captions = (1..3).map { index ->
            CaptionSegment("item-$index", (index - 1L) * 2_000_000L,
                index * 2_000_000L, SourceLanguage.INDONESIA,
                "Kalimat ke-$index", "", TranslationStatus.MISSING)
        }
        compose.setContent {
            MaterialTheme {
                Box(Modifier.size(360.dp, 580.dp)) {
                    EditorScreen(captions, CaptionStyle(), null, "Tersimpan", false,
                        {}, {}, {}, {}, demoMode = false)
                }
            }
        }
        compose.onNodeWithText("Daftar caption (3)").performClick()
        compose.onNodeWithTag("caption-list").assertIsDisplayed()
        compose.onNodeWithContentDescription("Caption berikutnya").assertIsDisplayed().performClick()
        compose.onNodeWithText("Caption 2 dari 3").assertIsDisplayed()
        compose.onNodeWithText("Kembali ke koreksi").assertDoesNotExist()
        compose.onNodeWithText("Teks asli").performScrollTo()
            .assertTextContains("Kalimat ke-2")
    }

    @Test fun studioSwitcherClearlySelectsCaptionTimingAndStyleWithoutLosingEdits() {
        val caption = CaptionSegment("studio", 0, 2_000_000, SourceLanguage.INDONESIA,
            "Kalimat awal", "", TranslationStatus.MISSING)
        var saved = listOf(caption)
        compose.setContent {
            MaterialTheme {
                Box(Modifier.size(360.dp, 640.dp)) {
                    EditorScreen(saved, CaptionStyle(), null, "Tersimpan", false,
                        { saved = it }, {}, {}, {}, demoMode = false)
                }
            }
        }
        compose.onNodeWithText("Teks").assertIsSelected()
        compose.onNodeWithText("KOREKSI CAPTION").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Teks asli").performScrollTo().performTextReplacement("Caption dikoreksi")
        compose.onNodeWithText("Waktu").performClick().assertIsSelected()
        compose.onNodeWithText("Gaya").performClick().assertIsSelected()
        compose.onNodeWithText("Teks").performClick().assertIsSelected()
        compose.onNodeWithText("Teks asli").performScrollTo().assertTextContains("Caption dikoreksi")
        compose.runOnIdle { assertTrue(saved.single().sourceText == "Caption dikoreksi") }
        compose.onNodeWithText("Ekspor").assertIsDisplayed()
    }

    @Test fun timingBoundaryCardsRetainNudgeConstraintsAtCompactFontScale() {
        val segment = CaptionSegment("timing", 0L, 2_000_000L, SourceLanguage.INDONESIA,
            "Caption pendek", "", TranslationStatus.MISSING)
        var result: Pair<Long, Long>? = null
        compose.setContent {
            val density = LocalDensity.current
            CompositionLocalProvider(LocalDensity provides Density(density.density, 1.5f)) {
                MaterialTheme {
                    Box(Modifier.size(320.dp, 480.dp)) {
                        TimingWorkspace(
                            segment = segment, minimumStartUs = 0L, maximumEndUs = 3_000_000L,
                            onChange = { start, end -> result = start to end },
                        )
                    }
                }
            }
        }
        compose.onNodeWithText("CAPTION TERPILIH").performScrollTo().assertExists()
        compose.onNodeWithText("Awal: 00:00.00").performScrollTo().assertExists()
        compose.onAllNodesWithText("-10 ms")[0].performScrollTo().assertIsNotEnabled()
        compose.onAllNodesWithText("+10 ms")[0].performScrollTo().performClick()
        compose.runOnIdle { assertTrue(result == (10_000L to 2_000_000L)) }
        compose.onNodeWithText("Akhir: 00:02.00").performScrollTo().assertExists()
        compose.onAllNodesWithText("+10 ms")[1].performScrollTo().performClick()
        compose.runOnIdle { assertTrue(result == (0L to 2_010_000L)) }
    }

    @Test fun styleSectionsRemainReachableAndPreserveStyleCallbacksAtLargeFont() {
        var style by mutableStateOf(CaptionStyle())
        compose.setContent {
            val density = LocalDensity.current
            CompositionLocalProvider(LocalDensity provides Density(density.density, 1.5f)) {
                MaterialTheme {
                    Box(Modifier.size(320.dp, 480.dp)) {
                        StyleWorkspace(style = style, onStyleChange = { style = it })
                    }
                }
            }
        }
        compose.onNodeWithText("Bahasa dan urutan").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Ukuran teks").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Keterbacaan dan posisi").performScrollTo().assertIsDisplayed()
        compose.onNodeWithContentDescription("Latar subtitle").performScrollTo().performClick()
        compose.runOnIdle { assertTrue(style.backgroundEnabled) }
        compose.onNodeWithText("Pratinjau dan MP4", substring = true).performScrollTo().assertIsDisplayed()
    }

    @Test fun videoPreviewUsesActualPortraitAndLandscapeAspectWithoutOversizing() {
        compose.setContent {
            MaterialTheme {
                androidx.compose.foundation.layout.Column(Modifier.size(360.dp, 660.dp)) {
                    VideoPreview(
                        segment = null, mediaUri = null, compactHeight = true,
                        videoWidth = 1080, videoHeight = 1920,
                        maxPreviewHeight = 248.dp,
                    )
                    VideoPreview(
                        segment = null, mediaUri = null, compactHeight = true,
                        videoWidth = 1920, videoHeight = 1080,
                        maxPreviewHeight = 112.dp,
                    )
                }
            }
        }
        val frames = compose.onAllNodesWithTag("video-preview-frame").fetchSemanticsNodes()
        assertTrue("Expected one correctly bounded frame for each video orientation", frames.size == 2)
        val portrait = frames[0].boundsInRoot
        val landscape = frames[1].boundsInRoot
        assertTrue("Portrait video should use its 9:16 aspect",
            kotlin.math.abs(portrait.width / portrait.height - 9f / 16f) < 0.04f)
        assertTrue("Landscape video should retain its 16:9 aspect",
            kotlin.math.abs(landscape.width / landscape.height - 16f / 9f) < 0.04f)
        assertTrue("Portrait video should receive meaningful extra height",
            portrait.height > landscape.height * 1.8f)
        assertTrue("Both frames must fit within the available 360dp width",
            portrait.width <= landscape.width + 1f)
    }

    @Test fun tallPortraitVideoKeepsWorkspaceAndExportReachableAtLargeFont() {
        val segment = CaptionSegment("portrait", 0L, 3_000_000L, SourceLanguage.INDONESIA,
            "Caption video vertikal", "Caption for portrait video", TranslationStatus.CURRENT)
        var exported = false
        compose.setContent {
            val density = LocalDensity.current
            CompositionLocalProvider(LocalDensity provides Density(density.density * 0.65f, 1.5f)) {
                MaterialTheme {
                    Box(Modifier.size(320.dp, 780.dp)) {
                        EditorScreen(
                            listOf(segment), CaptionStyle(), null, "Tersimpan", false,
                            {}, {}, {}, { exported = true },
                            demoMode = false, videoWidth = 1080, videoHeight = 1920,
                        )
                    }
                }
            }
        }
        val frame = compose.onNodeWithTag("video-preview-frame").fetchSemanticsNode().boundsInRoot
        val switcher = compose.onNodeWithText("Teks").fetchSemanticsNode().boundsInRoot
        assertTrue("Tall portrait video should not be squeezed into 16:9",
            kotlin.math.abs(frame.width / frame.height - 9f / 16f) < 0.04f)
        assertTrue("Preview must stop before studio workspace controls", frame.bottom <= switcher.top)
        compose.onNodeWithText("Teks asli").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Waktu").performClick()
        compose.onNodeWithText("Perubahan berhenti", substring = true).performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Gaya").performClick()
        compose.onNodeWithText("Pratinjau dan MP4", substring = true).performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Ekspor").assertIsDisplayed().performClick()
        compose.runOnIdle { assertTrue(exported) }
    }

    @Test fun machineMeaningWarningClearsWhenManualTranslationIsCorrected() {
        val caption = CaptionSegment(
            "meaning", 0L, 2_000_000L, SourceLanguage.INDONESIA,
            "Ibu tidak perlu mengantar saya.", "You don't have to take her.",
            TranslationStatus.CURRENT, TranslationOrigin.MACHINE_GEMMA, 2L, 2L,
        )
        var saved = listOf(caption)
        compose.setContent {
            MaterialTheme {
                Box(Modifier.size(360.dp, 640.dp)) {
                    EditorScreen(
                        listOf(caption), CaptionStyle(), null, "Tersimpan", false,
                        { saved = it }, {}, {}, {}, demoMode = false,
                    )
                }
            }
        }
        compose.onNodeWithText("Periksa makna terjemahan otomatis", substring = true)
            .performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Buka terjemahan", substring = true)
            .performScrollTo().performClick()
        compose.onNodeWithText("Terjemahan", substring = false)
            .performScrollTo().performTextReplacement("Mom, you don't need to take me.")
        compose.onNodeWithText("Periksa makna terjemahan otomatis", substring = true)
            .assertDoesNotExist()
        compose.runOnIdle {
            assertTrue(saved.single().translationOrigin == TranslationOrigin.MANUAL)
            assertTrue(saved.single().translationStatus == TranslationStatus.CURRENT)
            assertTrue(saved.single().translationText == "Mom, you don't need to take me.")
            assertTrue(!TranslationEligibility.canGenerate(saved.single(), true))
        }
    }

    @Test fun narrowShortEditorKeepsExportAndScrollableToolsReachableAtLargeFont() {
        var exported = false
        val caption = CaptionSegment("one", 0, 2_000_000, SourceLanguage.INDONESIA,
            "Kalimat panjang untuk pemeriksaan editor. ".repeat(10), "",
            TranslationStatus.MISSING)
        compose.setContent {
            val density = LocalDensity.current
            CompositionLocalProvider(LocalDensity provides Density(density.density, 1.5f)) {
                MaterialTheme {
                    Box(Modifier.size(320.dp, 480.dp)) {
                        EditorScreen(listOf(caption), CaptionStyle(), null, "Tersimpan", false,
                            {}, {}, {}, { exported = true },
                            demoMode = false,
                            projectTitle = "Judul proyek sangat panjang yang tidak boleh menimpa ekspor".repeat(3))
                    }
                }
            }
        }
        compose.onNodeWithText("Ekspor").assertIsDisplayed().performClick()
        compose.runOnIdle { assertTrue(exported) }
        val titleBounds = compose.onNodeWithText("Judul proyek", substring = true).fetchSemanticsNode().boundsInRoot
        val exportBounds = compose.onNodeWithText("Ekspor").fetchSemanticsNode().boundsInRoot
        assertTrue("Title must not overlap export", titleBounds.right <= exportBounds.left)
        compose.onNodeWithContentDescription("Kembali").assertIsDisplayed()
        compose.onNodeWithText("Teks").assertIsSelected()
        compose.onNodeWithText("Teks asli").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Gabung berikutnya").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Waktu").performClick()
        compose.onNodeWithText("Perubahan berhenti", substring = true).performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Gaya").performClick()
        compose.onNodeWithText("Terjemahan", substring = false).performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Pratinjau dan MP4", substring = true).performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Ekspor").assertIsDisplayed()
    }
}
