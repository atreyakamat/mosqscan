package com.vectora.ai.sync

import com.vectora.ai.data.local.db.SubmissionDao
import com.vectora.ai.data.local.db.SubmissionEntity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Manages synchronization between local Room storage and Vectora AI backend.
 * Local adult identification works completely offline; sync is an optional cloud backup.
 */
class SyncManager(
    private val submissionDao: SubmissionDao
) {

    data class SyncResult(
        val totalPending: Int,
        val syncedCount: Int,
        val failedCount: Int,
        val errorMessage: String? = null
    )

    suspend fun getPendingSyncCount(): Int = withContext(Dispatchers.IO) {
        val unsynced = submissionDao.getUnsyncedSubmissions()
        unsynced.size
    }

    suspend fun markSubmissionSynced(submissionId: String, remoteId: String) = withContext(Dispatchers.IO) {
        submissionDao.markSynced(submissionId, remoteId)
    }
}
