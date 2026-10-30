package app.subloka.engine.translation

internal object NativeGemma {
    init { System.loadLibrary("subloka_translation") }
    external fun open(path: String): Long
    external fun run(handle: Long, text: ByteArray, fromId: Boolean): ByteArray
    external fun cancel(handle: Long)
    external fun close(handle: Long)
}
