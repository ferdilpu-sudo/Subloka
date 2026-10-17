package app.subloka.core.media

import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import app.subloka.core.domain.*

/** Shared oriented-frame geometry for preview and encoded pixels. One instance per rendering thread. */
class SubtitlePainter(segments: List<CaptionSegment>, private val style: CaptionStyle) {
    private val segments = segments.sortedBy { it.startUs }
    private data class Line(val layout: StaticLayout, val color: Int)
    private data class Block(val lines: List<Line>, val height: Float, val width: Int, val gap: Float)
    private var key: Triple<String, Int, Int>? = null
    private var cached: Block? = null

    init {
        require(style.sourceSizePercent in 70..140 && style.translationSizePercent in 70..140 &&
            style.bottomPositionPercent in 8..35) { "Style subtitle di luar batas. Atur ulang di Style." }
    }
    fun validate(width: Int, height: Int) {
        segments.forEachIndexed { index, segment ->
            try { layout(segment, width, height) }
            catch (_: IllegalArgumentException) {
                throw IllegalArgumentException("Caption ${index + 1} terlalu panjang. Pecah caption atau kecilkan ukuran di Style.")
            }
        }
    }
    fun draw(canvas: Canvas, width: Int, height: Int, timeUs: Long) {
        val segment = segments.lastOrNull { it.startUs <= timeUs }?.takeIf { timeUs < it.endUs } ?: return
        val nextKey = Triple(segment.id, width, height)
        val block = if (key == nextKey) requireNotNull(cached) else layout(segment, width, height).also {
            key = nextKey; cached = it
        }
        val left = (width - block.width) / 2f
        val top = height * (1 - style.bottomPositionPercent / 100f) - block.height
        val padding = minOf(width, height) * .012f
        if (style.backgroundEnabled) canvas.drawRoundRect(left - padding, top - padding,
            left + block.width + padding, top + block.height + padding, padding, padding,
            Paint().apply { color = Color.argb(190, 0, 0, 0) })
        canvas.save()
        canvas.translate(left, top)
        block.lines.forEach { line ->
            val paint = line.layout.paint
            if (style.outlineEnabled) {
                paint.color = Color.BLACK; paint.style = Paint.Style.STROKE
                paint.strokeWidth = minOf(width, height) * .0035f
                paint.strokeJoin = Paint.Join.ROUND
                line.layout.draw(canvas)
            }
            paint.style = Paint.Style.FILL; paint.color = line.color
            line.layout.draw(canvas)
            canvas.translate(0f, line.layout.height + block.gap)
        }
        canvas.restore()
    }
    private fun layout(segment: CaptionSegment, width: Int, height: Int): Block {
        require(width > 0 && height > 0)
        val available = (width * .88f).toInt().coerceAtLeast(1)
        val size = minOf(width, height) * .043f
        fun line(text: String, percent: Int, color: Int): Line {
            require(text.isNotBlank()) { "Teks caption kosong." }
            val paint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
                textSize = size * percent / 100f
                typeface = Typeface.create("sans-serif", Typeface.BOLD)
            }
            val layout = StaticLayout.Builder.obtain(text, 0, text.length, paint, available)
                .setAlignment(Layout.Alignment.ALIGN_CENTER).setIncludePad(false)
                .setBreakStrategy(Layout.BREAK_STRATEGY_SIMPLE).build()
            require(layout.lineCount <= 4) { "Subtitle melampaui empat baris." }
            return Line(layout, color)
        }
        val source = { line(segment.sourceText, style.sourceSizePercent, Color.WHITE) }
        val translated = { line(segment.translationText, style.translationSizePercent, Color.rgb(255, 215, 100)) }
        val lines = when (style.displayMode) {
            CaptionDisplayMode.ORIGINAL -> listOf(source())
            CaptionDisplayMode.TRANSLATION -> listOf(translated())
            CaptionDisplayMode.DUAL -> if (style.order == CaptionOrder.SOURCE_FIRST)
                listOf(source(), translated()) else listOf(translated(), source())
        }
        val gap = size * .22f
        val total = lines.sumOf { it.layout.height }.toFloat() + gap * (lines.size - 1)
        require(total <= height * .5f) { "Subtitle menutupi lebih dari separuh video." }
        return Block(lines, total, available, gap)
    }
}
