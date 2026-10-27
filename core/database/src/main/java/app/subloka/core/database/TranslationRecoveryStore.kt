package app.subloka.core.database

import androidx.room.withTransaction
import app.subloka.core.domain.CaptionSegment
import app.subloka.core.domain.TranslationEligibility
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

/** Pending identities only: no duplicate source/translated text in the checkpoint. */
data class TranslationCheckpoint(val id: String, val engine: String, val total: Int,
                                 val pending: Map<String, Long>)

class TranslationRecoveryStore(private val database: SubLokaDatabase) {
    private val dao = database.processingJobDao()
    private val captions = RoomCaptionRepository(database)

    suspend fun recoverInterrupted() = dao.recoverTranslations(System.currentTimeMillis())
    suspend fun pending(projectId: String): TranslationCheckpoint? = dao.pendingTranslation(projectId)?.let(::decode)

    suspend fun begin(projectId: String, engine: String, snapshot: List<CaptionSegment>,
                      resumeId: String? = null): TranslationCheckpoint = database.withTransaction {
        val existing = dao.pendingTranslation(projectId)
        check(if (resumeId == null) existing == null else existing?.id == resumeId) { "Pekerjaan berubah. Buka ulang proyek." }
        val old = existing?.let(::decode)
        check(old == null || old.engine == engine) { "Gunakan model yang sama untuk melanjutkan." }
        val candidates = snapshot.filter { TranslationEligibility.canGenerate(it, true) &&
            (old == null || old.pending[it.id] == it.sourceRevision) }
        val items = candidates.associate { it.id to it.sourceRevision }
        val now = System.currentTimeMillis()
        if (existing != null) dao.save(existing.copy(state = "CANCELLED", stage = "SUPERSEDED", updated_at_ms = now))
        val checkpoint = TranslationCheckpoint(UUID.randomUUID().toString(), engine, items.size, items)
        val project = requireNotNull(database.projectDao().find(projectId))
        dao.save(ProcessingJobEntity(checkpoint.id, projectId, "TRANSLATE",
            if (items.isEmpty()) "SUCCEEDED" else "RUNNING", "TRANSLATE", if (items.isEmpty()) 1.0 else 0.0,
            project.content_revision, engine, engine, encode(checkpoint), null, now, now))
        checkpoint
    }

    /** Result and removal from pending work commit together, even when replacing CURRENT output. */
    suspend fun publish(jobId: String, source: CaptionSegment, text: String): Boolean = database.withTransaction {
        val job = requireNotNull(dao.find(jobId))
        check(job.state == "RUNNING")
        val checkpoint = decode(job)
        check(checkpoint.pending[source.id] == source.sourceRevision)
        val applied = captions.applyMachineTranslation(requireNotNull(job.project_id), source.id,
            source.sourceRevision, text, allowReplaceManual = false,
            origin = app.subloka.core.domain.TranslationOrigins.fromEngine(checkpoint.engine)) != null
        val remaining = checkpoint.copy(pending = checkpoint.pending - source.id)
        dao.save(job.copy(checkpoint_ref = encode(remaining),
            state = if (remaining.pending.isEmpty()) "SUCCEEDED" else "RUNNING",
            progress = (remaining.total - remaining.pending.size).toDouble() / remaining.total.coerceAtLeast(1),
            updated_at_ms = System.currentTimeMillis()))
        applied
    }

    suspend fun stop(jobId: String, interrupted: Boolean) = database.withTransaction {
        val job = dao.find(jobId) ?: return@withTransaction
        if (job.state == "RUNNING") dao.save(job.copy(state = if (interrupted) "INTERRUPTED" else "FAILED",
            error_code = if (interrupted) "PROCESS_INTERRUPTED" else "MODEL_FAILURE", updated_at_ms = System.currentTimeMillis()))
    }

    suspend fun discard(projectId: String) = database.withTransaction {
        dao.pendingTranslation(projectId)?.let { dao.save(it.copy(state = "CANCELLED", stage = "DISCARDED",
            updated_at_ms = System.currentTimeMillis())) }
    }

    private fun encode(value: TranslationCheckpoint): String = JSONObject().put("version", 1)
        .put("total", value.total).put("pending", JSONArray().also { array ->
            value.pending.forEach { (id, revision) -> array.put(JSONObject().put("id", id).put("revision", revision)) }
        }).toString()

    private fun decode(job: ProcessingJobEntity): TranslationCheckpoint {
        val json = JSONObject(requireNotNull(job.checkpoint_ref)); check(json.getInt("version") == 1)
        val array = json.getJSONArray("pending")
        val items = (0 until array.length()).associate { i ->
            val item = array.getJSONObject(i); item.getString("id") to item.getLong("revision")
        }
        return TranslationCheckpoint(job.id, requireNotNull(job.engine_version), json.getInt("total"), items)
    }
}
