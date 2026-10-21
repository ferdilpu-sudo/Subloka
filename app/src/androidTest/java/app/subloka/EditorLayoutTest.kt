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
import org.junit.Rule
import org.junit.Test
import org.junit.Assert.assertTrue

class EditorLayoutTest {
    @get:Rule val compose = createComposeRule()

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
        compose.onNodeWithText("VIDEO PREVIEW · PILIH VIDEO").assertIsDisplayed()
        compose.onNodeWithText("Teks asli").performScrollTo().assertIsDisplayed()
        val preview = compose.onNodeWithText("VIDEO PREVIEW · PILIH VIDEO").fetchSemanticsNode().boundsInRoot
        val field = compose.onNodeWithText("Teks asli").fetchSemanticsNode().boundsInRoot
        assertTrue("Landscape video and caption must be side by side", preview.right <= field.left)
        compose.onNodeWithText("Waktu").performScrollTo().performClick()
        compose.onNodeWithText("Perubahan berhenti", substring = true).performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Gaya").performClick()
        compose.onNodeWithText("Preview dan MP4", substring = true).performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("VIDEO PREVIEW · PILIH VIDEO").performScrollTo().assertIsDisplayed()
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
        compose.onNodeWithContentDescription("Caption berikutnya").performScrollTo().performClick()
        compose.onNodeWithText("Caption 2 dari 2").assertIsDisplayed()
        compose.onNodeWithContentDescription("Caption berikutnya").assertIsNotEnabled()
        compose.onNodeWithText("Gabung berikutnya").performScrollTo().assertIsNotEnabled()
        compose.onNodeWithContentDescription("Caption sebelumnya").performScrollTo().performClick()
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
        compose.onNodeWithText("Preview dan MP4", substring = true).performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Ekspor").assertIsDisplayed()
    }
}
