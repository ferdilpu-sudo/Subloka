pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "SubLoka"

include(":app")
include(":core:domain")
include(":core:designsystem")
include(":core:database")
include(":core:media")
include(":engine:asr")
include(":engine:translation")
include(":feature:projects")
include(":feature:editor")
include(":feature:export")
