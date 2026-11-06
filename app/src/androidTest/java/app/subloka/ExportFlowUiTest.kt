package app.subloka

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.SubLokaTheme
import app.subloka.core.domain.*
import app.subloka.demo.DemoData
import app.subloka.feature.export.ExportScreen
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class ExportFlowUiTest {
    @get:Rule val compose = createComposeRule()

    @Test fun staleTranslationDoesNotBlockOriginalOrSavingPreparedOutput() {
        var rendering by mutableStateOf(false)
        var ready by mutableStateOf(false)
        var pending by mutableStateOf(false)
        var documents by mutableStateOf(emptyList<SrtDocument>())
        var prepared: SrtExportMode? = null
        var rendered: SrtExportMode? = null
        var savedIndex: Int? = null
        var stops = 0
        var saves = 0
        compose.setContent {
            val density = LocalDensity.current
            CompositionLocalProvider(LocalDensity provides Density(density.density, 1.5f)) {
                SubLokaTheme {
                    Box(Modifier.size(320.dp, 480.dp)) {
                        ExportScreen(
                            segments = DemoData.segments, sourceLanguage = SourceLanguage.ENGLISH,
                            demoMode = false, busy = rendering, pending = pending,
                            documents = documents, saved = emptySet(), message = null,
                            onPrepare = { prepared = it }, onSave = { savedIndex = it }, onBack = {},
                            videoReady = ready, videoRendering = rendering, videoMessage = null, videoProgress = null,
                            onRender = { rendered = it }, onSaveVideo = { saves++ }, onCancelVideo = { stops++ },
                        )
                    }
                }
            }
        }
        compose.onNodeWithText("Siapkan SRT").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(SrtExportMode.SOURCE, prepared) }
        compose.onNodeWithText("Keduanya").performScrollTo().performClick()
        compose.onNodeWithText("Siapkan SRT").assertIsNotEnabled()
        compose.runOnIdle { documents = listOf(SrtDocument("fixture.en.srt", "fixture")) }
        compose.onNodeWithText("Simpan SRT Inggris").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(0, savedIndex) }
        compose.onNodeWithText("MP4").performScrollTo().performClick()
        compose.onNodeWithText("Render MP4").assertIsNotEnabled()
        compose.onNodeWithText("Asli (${SourceLanguage.ENGLISH.label})").performScrollTo().performClick()
        compose.onNodeWithText("Render MP4").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(SrtExportMode.SOURCE, rendered); rendering = true }
        compose.onNodeWithText("Hentikan render").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(1, stops); rendering = false; ready = true }
        compose.onNodeWithText("Keduanya").performScrollTo().performClick()
        compose.onNodeWithText("Render ulang dengan pilihan ini").performScrollTo().assertIsNotEnabled()
        compose.onNodeWithText("Simpan MP4").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(1, saves); pending = true }
        compose.onNodeWithText("Simpan MP4").assertIsNotEnabled()
        compose.runOnIdle { pending = false }
        compose.onNodeWithText("Simpan MP4").performClick()
        compose.runOnIdle { assertEquals(2, saves) }
    }

    @Test fun preparedBothSrtPrioritizesUnsavedLanguageAndKeepsPreparedFiles() {
        val first = CaptionSegment("one", 0L, 1_500_000L, SourceLanguage.INDONESIA,
            "Halo", "Hello", TranslationStatus.CURRENT, TranslationOrigin.MANUAL, 1L, 1L)
        var documents by mutableStateOf(emptyList<SrtDocument>())
        var saved by mutableStateOf(emptySet<Int>())
        var pending by mutableStateOf(false)
        var selectedSave: Int? = null
        var back = 0
        var prepareCalls = 0
        compose.setContent {
            val density = LocalDensity.current
            CompositionLocalProvider(LocalDensity provides Density(density.density, 1.5f)) {
                SubLokaTheme {
                    Box(Modifier.size(320.dp, 560.dp)) {
                        ExportScreen(
                            segments = listOf(first), sourceLanguage = SourceLanguage.INDONESIA,
                            demoMode = false, busy = false, pending = pending,
                            documents = documents, saved = saved, message = null,
                            onPrepare = { mode ->
                                prepareCalls++
                                documents = SrtExport.documents("7", SourceLanguage.INDONESIA,
                                    2_000_000L, listOf(first), mode)
                                saved = emptySet()
                            },
                            onSave = { index -> selectedSave = index; pending = true },
                            onBack = { back++ }, videoReady = false, videoRendering = false,
                            videoMessage = null, videoProgress = null,
                            onRender = {}, onSaveVideo = {}, onCancelVideo = {},
                        )
                    }
                }
            }
        }
        compose.onNodeWithText("Keduanya").performScrollTo().performClick()
        compose.onNodeWithText("Siapkan SRT").assertIsDisplayed().performClick()
        compose.runOnIdle {
            assertEquals(1, prepareCalls)
            assertEquals(listOf("7.id.srt", "7.en.srt"), documents.map { it.name })
        }
        compose.onNodeWithText("SRT siap disimpan").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("0 dari 2 file tersimpan.").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Simpan SRT Indonesia").assertIsDisplayed()
        compose.onNodeWithText("Simpan SRT Inggris").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Siapkan SRT lagi").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Simpan SRT Indonesia").performClick()
        compose.runOnIdle {
            assertEquals(0, selectedSave)
            assertTrue(pending)
        }
        compose.onNodeWithText("Simpan SRT Indonesia").assertIsNotEnabled()
        // Simulate picker cancellation: no success should appear or be counted.
        compose.runOnIdle { pending = false }
        compose.onNodeWithText("0 dari 2 file tersimpan.").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Simpan SRT Indonesia").performClick()
        compose.runOnIdle { pending = false; saved = setOf(0) }
        compose.onNodeWithText("1 dari 2 file tersimpan.").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Simpan ulang SRT Indonesia").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Simpan SRT Inggris").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(1, selectedSave); pending = false; saved = setOf(0, 1) }
        compose.onNodeWithText("2 dari 2 file tersimpan.").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Selesai — kembali ke editor").assertIsDisplayed().performClick()
        compose.runOnIdle {
            assertEquals(1, back)
            assertEquals(1, prepareCalls)
            assertEquals(listOf("7.id.srt", "7.en.srt"), documents.map { it.name })
        }
    }

    @Test fun preparedSrtCanBeSavedEvenAfterCurrentSelectionChanges() {
        val caption = CaptionSegment("en", 0L, 1_500_000L, SourceLanguage.ENGLISH,
            "Hello", "Halo", TranslationStatus.CURRENT, TranslationOrigin.MANUAL, 1L, 1L)
        var chosen: Int? = null
        val files = SrtExport.documents("7", SourceLanguage.ENGLISH, 2_000_000L,
            listOf(caption), SrtExportMode.BOTH)
        compose.setContent {
            SubLokaTheme {
                ExportScreen(
                    segments = listOf(caption), sourceLanguage = SourceLanguage.ENGLISH,
                    demoMode = false, busy = false, pending = false,
                    documents = files, saved = setOf(0), message = null,
                    onPrepare = {}, onSave = { chosen = it }, onBack = {},
                    videoReady = false, videoRendering = false,
                    videoMessage = null, videoProgress = null,
                    onRender = {}, onSaveVideo = {}, onCancelVideo = {},
                )
            }
        }
        // The English-original file was saved, so the prepared Indonesian
        // translation is the next action regardless of the selected radio.
        compose.onNodeWithText("Simpan SRT Indonesia").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(1, chosen) }
    }

    @Test fun historicalGoogleNoticeFollowsTranslationSelection() {
        val rows = listOf(
            CaptionSegment("google", 0, 1_000_000, SourceLanguage.ENGLISH, "Hello", "Halo",
                TranslationStatus.CURRENT, TranslationOrigin.MACHINE_MLKIT, 1, 1),
            CaptionSegment("gemma", 1_000_000, 2_000_000, SourceLanguage.ENGLISH, "Thanks", "Terima kasih",
                TranslationStatus.CURRENT, TranslationOrigin.MACHINE_GEMMA, 1, 1)
        )
        compose.setContent {
            SubLokaTheme {
                ExportScreen(
                    segments = rows, sourceLanguage = SourceLanguage.ENGLISH,
                    demoMode = false, busy = false, pending = false,
                    documents = emptyList(), saved = emptySet(), message = null,
                    onPrepare = {}, onSave = {}, onBack = {},
                    videoReady = false, videoRendering = false,
                    videoMessage = null, videoProgress = null,
                    onRender = {}, onSaveVideo = {}, onCancelVideo = {},
                )
            }
        }
        compose.onNodeWithText("1 caption hasil lama Google Translate (ML Kit)", substring = true).assertDoesNotExist()
        compose.onNodeWithText("2 caption berisi terjemahan otomatis", substring = true).assertDoesNotExist()
        compose.onNodeWithText("Terjemahan (Indonesia)").performScrollTo().performClick()
        compose.onNodeWithText("1 caption hasil lama Google Translate (ML Kit)", substring = true)
            .performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("2 caption berisi terjemahan otomatis", substring = true)
            .performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Asli (English)").performScrollTo().performClick()
        compose.onNodeWithText("1 caption hasil lama Google Translate (ML Kit)", substring = true).assertDoesNotExist()
        compose.onNodeWithText("2 caption berisi terjemahan otomatis", substring = true).assertDoesNotExist()
    }


    @Test fun exportSectionsPreserveProviderWarningsAndFixedActionAtLargeFont() {
        val captions = listOf(
            CaptionSegment("google", 0L, 1_000_000L, SourceLanguage.INDONESIA, "Halo", "Hello",
                TranslationStatus.CURRENT, TranslationOrigin.MACHINE_MLKIT, 1L, 1L),
            CaptionSegment("unknown", 1_000_000L, 2_000_000L, SourceLanguage.INDONESIA, "Apa kabar", "How are you",
                TranslationStatus.CURRENT, TranslationOrigin.MACHINE, 1L, 1L),
            CaptionSegment("manual", 2_000_000L, 3_000_000L, SourceLanguage.INDONESIA, "Terima kasih", "Thanks",
                TranslationStatus.CURRENT, TranslationOrigin.MANUAL, 1L, 1L)
        )
        var prepared: SrtExportMode? = null
        var rendered: SrtExportMode? = null
        compose.setContent {
            val density = LocalDensity.current
            CompositionLocalProvider(LocalDensity provides Density(density.density, 1.5f)) {
                SubLokaTheme {
                    Box(Modifier.size(320.dp, 480.dp)) {
                        ExportScreen(
                            segments = captions, sourceLanguage = SourceLanguage.INDONESIA,
                            demoMode = false, busy = false, pending = false,
                            documents = emptyList(), saved = emptySet(), message = null,
                            onPrepare = { prepared = it }, onSave = {}, onBack = {},
                            videoReady = false, videoRendering = false,
                            videoMessage = null, videoProgress = null,
                            onRender = { rendered = it }, onSaveVideo = {}, onCancelVideo = {},
                        )
                    }
                }
            }
        }
        compose.onNodeWithText("Format hasil").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Bahasa caption").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("File SRT").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Asal terjemahan").assertDoesNotExist()
        compose.onNodeWithText("Terjemahan (English)").performScrollTo().performClick()
        compose.onNodeWithText("Asal terjemahan").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("1 caption hasil lama Google Translate (ML Kit)", substring = true)
            .performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("1 caption terjemahan otomatis tidak memiliki catatan penyedia", substring = true)
            .performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Siapkan SRT").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(SrtExportMode.TRANSLATION, prepared) }
        compose.onNodeWithText("MP4").performScrollTo().performClick()
        compose.onNodeWithText("Hasil video").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Render MP4").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(SrtExportMode.TRANSLATION, rendered) }
        compose.onNodeWithText("Asli (Indonesia)").performScrollTo().performClick()
        compose.onNodeWithText("Asal terjemahan").assertDoesNotExist()
    }

}
