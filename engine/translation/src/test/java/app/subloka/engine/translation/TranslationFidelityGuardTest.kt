package app.subloka.engine.translation

import app.subloka.core.domain.SourceLanguage
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TranslationFidelityGuardTest {
    private fun flags(source: String, target: String, language: SourceLanguage = SourceLanguage.INDONESIA) =
        TranslationFidelityGuard.inspect(source, target, language).map { it.concern }.toSet()

    @Test fun futureTimeAndWrongPastFlagged() {
        assertTrue(TranslationFidelityGuard.Concern.TEMPORAL_CONTRADICTION in
            flags("Paket sampai besok pagi.", "The package arrived tomorrow morning."))
    }

    @Test fun futureMarkerDoesNotFlagProperFuture() {
        assertFalse(TranslationFidelityGuard.Concern.TEMPORAL_CONTRADICTION in
            flags("Paket sampai besok pagi.", "The package will arrive tomorrow morning."))
    }

    @Test fun strongProhibitionAndWeakSuggestionFlagged() {
        assertTrue(TranslationFidelityGuard.Concern.PROHIBITION_POSSIBLY_WEAKENED in
            flags("Penghapusan tidak boleh dilanjutkan.", "Deletion should not proceed."))
    }

    @Test fun equivalentStrongProhibitionNotFlagged() {
        assertFalse(TranslationFidelityGuard.Concern.PROHIBITION_POSSIBLY_WEAKENED in
            flags("Tidak boleh membuka berkas ini.", "You must not open this file."))
        assertFalse(TranslationFidelityGuard.Concern.PROHIBITION_POSSIBLY_WEAKENED in
            flags("Do not discard the source.", "Jangan buang sumber.", SourceLanguage.ENGLISH))
    }

    @Test fun negationLostFlaggedInBothDirections() {
        assertTrue(TranslationFidelityGuard.Concern.NEGATION_POSSIBLY_DROPPED in
            flags("Jangan simpan duplikat.", "Save a duplicate."))
        assertTrue(TranslationFidelityGuard.Concern.NEGATION_POSSIBLY_DROPPED in
            flags("This is not a final draft.", "Ini adalah draf final.", SourceLanguage.ENGLISH))
    }

    @Test fun negationPreservedNotFlagged() {
        assertFalse(TranslationFidelityGuard.Concern.NEGATION_POSSIBLY_DROPPED in
            flags("Saya tidak memiliki tiket.", "I do not have a ticket."))
    }

    @Test fun numberMismatchDetectsThousandsDifferentSeparator() {
        assertTrue(TranslationFidelityGuard.Concern.NUMBER_TOKEN_MISMATCH in
            flags("Transfer 125.000 rupiah.", "Transfer 152,000 rupiah."))
        assertFalse(TranslationFidelityGuard.Concern.NUMBER_TOKEN_MISMATCH in
            flags("Transfer 125.000 rupiah.", "Transfer 125,000 rupiah."))
    }

    @Test fun missingDigitInTargetFlagsReviewWithoutAlteringOutput() {
        assertTrue(TranslationFidelityGuard.Concern.NUMBER_TOKEN_MISMATCH in
            flags("Harga tiket 17 rupiah.", "The ticket costs seventeen rupiah."))
    }

    @Test fun ambiguousGenderFlaggedButNotChanged() {
        val text = "My sister is waiting."
        val assessment = TranslationFidelityGuard.inspect("Adik saya sedang menunggu.", text,
            SourceLanguage.INDONESIA)
        assertTrue(assessment.any { it.concern == TranslationFidelityGuard.Concern.GENDER_ASSUMPTION })
        assertEquals("My sister is waiting.", text)
    }

    @Test fun noGenderAssumptionWhenTargetNeutral() {
        assertFalse(TranslationFidelityGuard.Concern.GENDER_ASSUMPTION in
            flags("Adik saya menunggu.", "My younger sibling is waiting."))
    }

    @Test fun untranslatedGenericTransportAndAdministrativeTermsFlagged() {
        assertTrue(TranslationFidelityGuard.Concern.POSSIBLY_UNTRANSLATED_TERM in
            flags("Petugas ada di peron dua.", "The staff is on Peron two."))
        assertTrue(TranslationFidelityGuard.Concern.POSSIBLY_UNTRANSLATED_TERM in
            flags("Silakan datang ke kecamatan.", "Please come to the kecamatan."))
    }

    @Test fun translatedTransportTermsDoNotFlag() {
        assertFalse(TranslationFidelityGuard.Concern.POSSIBLY_UNTRANSLATED_TERM in
            flags("Petugas ada di peron dua.", "The staff is on platform two."))
    }

    @Test fun temporalEnglishToIndonesian() {
        assertTrue(TranslationFidelityGuard.Concern.TEMPORAL_CONTRADICTION in
            flags("She will come tomorrow.", "Dia datang kemarin.", SourceLanguage.ENGLISH))
        assertFalse(TranslationFidelityGuard.Concern.TEMPORAL_CONTRADICTION in
            flags("She will come tomorrow.", "Dia akan datang besok.", SourceLanguage.ENGLISH))
    }

    @Test fun blankInputProducesNoFlags() {
        assertTrue(flags(" ", "any output").isEmpty())
        assertTrue(flags("source", " ").isEmpty())
    }

    @Test fun impossibleToProveSemanticEquivalenceFromHeuristics() {
        // A plausible word-change is missed; the absence of flags NEVER means ACCEPT.
        assertTrue(flags("Bus berhenti di kota.", "The bus stopped at a village.").isEmpty())
    }
}
