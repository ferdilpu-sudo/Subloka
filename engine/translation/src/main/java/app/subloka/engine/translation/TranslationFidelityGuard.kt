package app.subloka.engine.translation

import app.subloka.core.domain.SourceLanguage

/**
 * Conservative, offline-only QA hints for potentially unsafe translations.
 *
 * Not a translation engine, grammar checker, correctness proof, or replacement for a
 * bilingual reviewer. False positives and false negatives are expected. Do not
 * silently rewrite text, or count these flags as acceptance-gate failures/passes.
 * No benchmark-specific sample IDs, whole phrases, or fixed output corrections.
 */
object TranslationFidelityGuard {
    enum class Concern {
        NUMBER_TOKEN_MISMATCH,
        NEGATION_POSSIBLY_DROPPED,
        PROHIBITION_POSSIBLY_WEAKENED,
        TEMPORAL_CONTRADICTION,
        GENDER_ASSUMPTION,
        POSSIBLY_UNTRANSLATED_TERM,
    }

    data class Flag(val concern: Concern, val explanation: String)

    private val numberToken = Regex("(?<![\\p{L}\\p{N}])\\d+(?:[.,]\\d+)*(?![\\p{L}\\p{N}])")
    private val thousandGrouped = Regex("\\d{1,3}(?:[.,]\\d{3})+")
    private val enNegation = Regex("\\b(?:no|not|never|without|cannot|can't|won't|don't|doesn't|didn't|isn't|aren't|wasn't|weren't|mustn't|shouldn't)\\b")
    private val idNegation = Regex("\\b(?:tidak|bukan|belum|jangan|tak|tanpa)\\b")
    private val enStrongProhibition = Regex("\\b(?:must\\s+not|mustn't|prohibited|not\\s+allowed|forbidden)\\b")
    private val enImperativeProhibition = Regex("^(?:please\\s+)?(?:do\\s+not|don't)\\b")
    private val idStrongProhibition = Regex("\\b(?:tidak\\s+boleh|jangan|dilarang|tidak\\s+diizinkan)\\b")
    private val enWeakProhibition = Regex("\\b(?:should\\s+not|shouldn't|better\\s+not)\\b")
    private val idWeakProhibition = Regex("\\b(?:sebaiknya\\s+tidak|seharusnya\\s+tidak)\\b")
    private val enPastConflictsTomorrow = Regex("\\b(?:began|started|ended|finished|arrived|happened|was|were|had)\\b")
    private val enFutureMarker = Regex("\\b(?:will|shall|going\\s+to|scheduled\\s+to)\\b")
    private val genderedEnglish = Regex("\\b(?:brother|sister|he|she|him|her|his|hers)\\b")
    // Domain hints for UI/transport/administration. These are warnings only, not
    // a benchmark-specific replacement dictionary. Proper names are ignored.
    private val potentiallyUntranslated = setOf(
        "peron", "kereta", "jadwal", "puskesmas", "kecamatan", "kelurahan",
        "tagihan", "berkas", "rapat", "jembatan", "rekaman",
    )

    fun inspect(
        sourceText: String,
        translatedText: String,
        sourceLanguage: SourceLanguage,
    ): List<Flag> {
        if (sourceText.isBlank() || translatedText.isBlank()) return emptyList()
        val source = sourceText.lowercase()
        val target = translatedText.lowercase()
        val sourceNumbers = numericTokens(source)
        val translatedNumbers = numericTokens(target)
        val result = mutableListOf<Flag>()
        if (sourceNumbers.isNotEmpty() && translatedNumbers.isNotEmpty() &&
            sourceNumbers != translatedNumbers
        ) {
            result += Flag(Concern.NUMBER_TOKEN_MISMATCH,
                "Digit tokens differ; inspect amount, date and unit manually")
        } else if (sourceNumbers.isNotEmpty() && translatedNumbers.isEmpty()) {
            // The target might spell out the number; the signal is conservative.
            result += Flag(Concern.NUMBER_TOKEN_MISMATCH,
                "Source has digit tokens but translation does not; check spelled-out numbers")
        }
        val isId = sourceLanguage == SourceLanguage.INDONESIA
        val sourceNegative = if (isId) idNegation.containsMatchIn(source) else enNegation.containsMatchIn(source)
        val targetNegative = if (isId) enNegation.containsMatchIn(target) else idNegation.containsMatchIn(target)
        if (sourceNegative && !targetNegative) {
            result += Flag(Concern.NEGATION_POSSIBLY_DROPPED,
                "Negative meaning may be absent in translated output")
        }
        val sourceProhibition = if (isId) idStrongProhibition.containsMatchIn(source) else (enStrongProhibition.containsMatchIn(source) || enImperativeProhibition.containsMatchIn(source))
        val targetProhibition = if (isId) (enStrongProhibition.containsMatchIn(target) || enImperativeProhibition.containsMatchIn(target)) else idStrongProhibition.containsMatchIn(target)
        val targetWeak = if (isId) enWeakProhibition.containsMatchIn(target) else idWeakProhibition.containsMatchIn(target)
        if (sourceProhibition && (!targetProhibition || targetWeak)) {
            result += Flag(Concern.PROHIBITION_POSSIBLY_WEAKENED,
                "A strong source prohibition may have become a weaker suggestion")
        }
        if (isId) {
            if (word(source, "besok") && enPastConflictsTomorrow.containsMatchIn(target) &&
                !enFutureMarker.containsMatchIn(target)
            ) {
                result += Flag(Concern.TEMPORAL_CONTRADICTION,
                    "Source says tomorrow but target has potentially conflicting past tense")
            }
            if (word(source, "kemarin") && enFutureMarker.containsMatchIn(target)) {
                result += Flag(Concern.TEMPORAL_CONTRADICTION,
                    "Source says yesterday but target appears to refer to future")
            }
            if ((word(source, "adik") || word(source, "dia")) && genderedEnglish.containsMatchIn(target)) {
                result += Flag(Concern.GENDER_ASSUMPTION,
                    "Gender-neutral Indonesian source may have acquired gender in English")
            }
            if (potentiallyUntranslated.any { word(source, it) && word(target, it) }) {
                result += Flag(Concern.POSSIBLY_UNTRANSLATED_TERM,
                    "Indonesian administrative, media or transport term might remain untranslated")
            }
        } else {
            if (word(source, "tomorrow") && word(target, "kemarin")) {
                result += Flag(Concern.TEMPORAL_CONTRADICTION,
                    "Source says tomorrow but target says yesterday")
            }
            if (word(source, "yesterday") && word(target, "besok")) {
                result += Flag(Concern.TEMPORAL_CONTRADICTION,
                    "Source says yesterday but target says tomorrow")
            }
        }
        return result.distinctBy { it.concern }
    }

    private fun word(text: String, token: String): Boolean =
        Regex("(?<![\\p{L}])" + Regex.escape(token) + "(?![\\p{L}])").containsMatchIn(text)

    private fun numericTokens(text: String): List<String> =
        numberToken.findAll(text).map { match ->
            val number = match.value
            if (thousandGrouped.matches(number)) number.replace(",", "").replace(".", "")
            else number.replace(",", ".")
        }.toList()
}
