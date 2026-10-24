package app.subloka.engine.asr

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

class WhisperModelStore(
    private val directory: File,
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
            } else if (sha256(target) == model.expectedSha256) {
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
            val maxBytes = model.expectedSizeBytes ?: (200L * 1024 * 1024)
            FileOutputStream(temp).use { output ->
                val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                while (true) {
                    currentCoroutineContext().ensureActive()
                    val count = input.read(buffer)
                    if (count < 0) break
                    if (count == 0) continue
                    check(count.toLong() <= maxBytes - written) { "Model exceeds storage limit" }
                    output.write(buffer, 0, count)
                    written += count
                    digest.update(buffer, 0, count)
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
                readTimeout = 60_000
                instanceFollowRedirects = true
                requestMethod = "GET"
            }

            try {
                connection.connect()
                require(connection.responseCode in 200..299) {
                    "Model download failed: HTTP ${connection.responseCode}"
                }
                connection.inputStream.use { input ->
                    installFrom(model, input)
                }
            } finally {
                connection.disconnect()
            }
        }

    fun targetFile(model: ManagedModelDescriptor): File =
        File(directory, model.fileName)

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            while (true) {
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
