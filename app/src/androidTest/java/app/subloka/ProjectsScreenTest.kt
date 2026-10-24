package app.subloka

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.SubLokaTheme
import app.subloka.core.domain.ProjectSummary
import app.subloka.core.domain.SourceLanguage
import app.subloka.feature.projects.ProjectsScreen
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

class ProjectsScreenTest {
    @get:Rule val compose = createComposeRule()

    @Test fun emptyProjectsKeepsCreateActionReachableAtLargeFont() {
        var created = false
        compose.setContent {
            val density = LocalDensity.current
            CompositionLocalProvider(LocalDensity provides Density(density.density, 1.5f)) {
                SubLokaTheme {
                    Box(Modifier.size(320.dp, 480.dp)) {
                        ProjectsScreen(emptyList(), { created = true }, {})
                    }
                }
            }
        }
        compose.onNodeWithText("Belum ada proyek").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Proyek baru").assertIsDisplayed().performClick()
        compose.runOnIdle { assertTrue(created) }
    }

    @Test fun longListOpensCorrectProjectAndKeepsCreateActionVisible() {
        val projects = (1..30).map {
            ProjectSummary("project-$it", "Proyek $it", "video-$it.mp4", SourceLanguage.INDONESIA,
                "02:00", "1920 × 1080", "Diperbarui 22/10/2026", "Tersimpan di perangkat")
        }
        var opened: String? = null
        var created = false
        compose.setContent {
            SubLokaTheme {
                Box(Modifier.size(320.dp, 480.dp)) {
                    ProjectsScreen(projects, { created = true }, { opened = it.id })
                }
            }
        }
        compose.onNode(hasScrollToNodeAction()).performScrollToNode(hasText("Proyek 25"))
        compose.onNodeWithText("Proyek 25").performClick()
        compose.runOnIdle { assertEquals("project-25", opened) }
        compose.onNodeWithText("Proyek baru").assertIsDisplayed().performClick()
        compose.runOnIdle { assertTrue(created) }
    }
}
