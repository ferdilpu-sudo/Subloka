package app.subloka.engine.translation

import app.subloka.core.domain.ManagedModelDescriptor
import app.subloka.core.domain.ModelReadinessState
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class TranslationModelStore(
    private val directory: File,
    private val checkTransfer: () -> Unit = {},
    private val progress: (Int) -> Unit = {},
) {
    init {
        require(directory.exists() || directory.mkdirs()) { "Cannot create model directory: $directory" }
        require(directory.isDirectory) { "Model path is not a directory: $directory" }
    }

    suspend fun state(model: ManagedModelDescriptor): ModelReadinessState =
        withContext(Dispatchers.IO) {
            val target = targetFile(model)
            if (!target.isFile) {
                ModelReadinessState.NOT_READY
            } else if ((model.expectedSizeBytes == null || target.length() == model.expectedSizeBytes) && sha256(target) == model.expectedSha256) {
                ModelReadinessState.READY
            } else {
                ModelReadinessState.FAILED
            }
        }

    suspend fun installFrom(
        model: ManagedModelDescriptor,
        input: InputStream,
    ): File = withContext(Dispatchers.IO) {
        val target = targetFile(model)
        val temp = File(directory, "${model.fileName}.part")
        temp.delete()

        try {
            val digest = MessageDigest.getInstance("SHA-256")
            var written = 0L
            val maxBytes = requireNotNull(model.expectedSizeBytes)
            var lastPercent = -1
            FileOutputStream(temp).use { output ->
                val buffer = ByteArray(256 * 1024)
                while (true) {
                    currentCoroutineContext().ensureActive()
                    checkTransfer()
                    val count = input.read(buffer)
                    if (count < 0) break
                    if (count == 0) continue
                    check(count.toLong() <= maxBytes - written) { "Model exceeds storage limit" }
                    output.write(buffer, 0, count)
                    written += count
                    digest.update(buffer, 0, count)
                    val percent = (written * 100 / maxBytes).toInt()
                    if (percent != lastPercent) { progress(percent); lastPercent = percent }
                }
                output.fd.sync()
            }

            require(model.expectedSizeBytes == null || written == model.expectedSizeBytes) { "Model size mismatch" }
            val actual = digest.digest().toHex()
            require(actual == model.expectedSha256) {
                "Model checksum mismatch for ${model.id}: expected ${model.expectedSha256}, got $actual"
            }

            currentCoroutineContext().ensureActive()
            Files.move(temp.toPath(), target.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
            target
        } catch (error: Throwable) {
            temp.delete()
            throw error
        }
    }

    suspend fun download(model: ManagedModelDescriptor): File =
        withContext(Dispatchers.IO) {
            val connection = (URL(model.downloadUrl).openConnection() as HttpURLConnection).apply {
                connectTimeout = 15_000
                readTimeout = 30_000
                instanceFollowRedirects = true
                requestMethod = "GET"
            }

            try {
                require(URL(model.downloadUrl).protocol == "https")
                checkTransfer()
                connection.connect()
                require(connection.responseCode in 200..299) {
                    "Model download failed: HTTP ${connection.responseCode}"
                }
                require(connection.contentLengthLong < 0 || connection.contentLengthLong == model.expectedSizeBytes) { "Model size mismatch" }
                connection.inputStream.use { input ->
                    installFrom(model, input)
                }
            } finally {
                connection.disconnect()
            }
        }

    fun targetFile(model: ManagedModelDescriptor): File =
        File(directory, model.fileName)

    private suspend fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(256 * 1024)
            while (true) {
                currentCoroutineContext().ensureActive()
                val count = input.read(buffer)
                if (count < 0) break
                if (count > 0) digest.update(buffer, 0, count)
            }
        }
        return digest.digest().toHex()
    }

    private fun ByteArray.toHex(): String =
        joinToString(separator = "") { byte -> "%02x".format(byte.toInt() and 0xff) }
}
