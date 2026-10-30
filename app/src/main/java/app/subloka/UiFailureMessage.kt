package app.subloka

import app.subloka.core.domain.MediaSourceException
import app.subloka.core.domain.MediaErrorCode

/** User recovery guidance; never exposes an arbitrary native/platform exception message. */
internal object UiFailureMessage {
    private val actionable = setOf(
        "Model tidak tersedia. Siapkan kembali model.",
        "Video berubah. Buat proyek baru dari video ini.",
        "Proyek berubah. Hasil tidak mengganti caption yang sudah ada.",
        "Proyek berubah. Buka kembali proyek yang ingin ditautkan.",
        "Identitas video lama tidak tersedia. Penautan ulang aman tidak dapat dilakukan.",
        "Video berbeda dari sumber asli. Pilih file asli yang sama; caption tidak diubah.",
        "Izin video tidak dapat disimpan. Pilih file dari penyimpanan perangkat.",
        "Sumber proyek berubah. Coba tautkan ulang kembali.",
    )

    fun describe(error: Throwable, fallback: String): String {
        // Type only: filenames, paths, captions and model internals are not logged.
        android.util.Log.w("SubLokaFailure", error.javaClass.simpleName)
        return when (error) {
            is MediaSourceException -> when (error.code) {
                MediaErrorCode.NO_AUDIO -> "Video tidak memiliki audio. Pilih video dengan suara untuk membuat caption."
                MediaErrorCode.URI_PERMISSION_LOST -> "Akses video berakhir. Pilih kembali video atau tautkan file aslinya."
                MediaErrorCode.MEDIA_UNAVAILABLE -> "Video tidak dapat diakses. Pilih kembali video atau tautkan file aslinya."
                MediaErrorCode.UNSUPPORTED_MEDIA -> "Format video belum didukung. Pilih video lain yang dapat diputar di perangkat."
                MediaErrorCode.DECODE_FAILURE -> "Audio video tidak dapat dibaca. Coba video lain."
            }
            is android.database.sqlite.SQLiteFullException ->
                "Penyimpanan penuh. Kosongkan ruang, lalu coba lagi."
            is SecurityException ->
                "Akses berkas ditolak. Pilih kembali berkas atau lokasi penyimpanan."
            is java.io.FileNotFoundException ->
                "Berkas tidak dapat diakses. Pilih kembali berkas atau lokasi penyimpanan."
            else -> error.message?.takeIf { it in actionable } ?: fallback
        }
    }
}
