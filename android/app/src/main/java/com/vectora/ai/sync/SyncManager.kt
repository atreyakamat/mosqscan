package com.vectora.ai.sync

import com.vectora.ai.data.local.db.SubmissionDao
import com.vectora.ai.data.local.db.SubmissionEntity
import com.vectora.ai.data.remote.ServerClientManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File

/**
 * Manages synchronization between local Room storage and Vectora AI backend.
 * Provides offline-first submission queuing and deterministic server synchronization.
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

    suspend fun syncAllPending(serverClientManager: ServerClientManager): SyncResult = withContext(Dispatchers.IO) {
        val unsynced = submissionDao.getUnsyncedSubmissions()
        if (unsynced.isEmpty()) {
            return@withContext SyncResult(0, 0, 0)
        }

        var synced = 0
        var failed = 0
        var lastError: String? = null

        val service = serverClientManager.getService()

        for (sub in unsynced) {
            try {
                if (sub.type == "adult" && sub.imagePath != null) {
                    val file = File(sub.imagePath)
                    if (!file.exists()) {
                        failed++
                        continue
                    }

                    val requestFile = file.asRequestBody("image/jpeg".toMediaTypeOrNull())
                    val body = MultipartBody.Part.createFormData("file", file.name, requestFile)
                    val cropX = sub.cropX?.toString()?.toRequestBody("text/plain".toMediaTypeOrNull())
                    val cropY = sub.cropY?.toString()?.toRequestBody("text/plain".toMediaTypeOrNull())
                    val cropW = sub.cropW?.toString()?.toRequestBody("text/plain".toMediaTypeOrNull())
                    val cropH = sub.cropH?.toString()?.toRequestBody("text/plain".toMediaTypeOrNull())

                    val response = service.submitAdult(body, cropX, cropY, cropW, cropH)
                    if (response.isSuccessful && response.body() != null) {
                        val respBody = response.body()!!
                        val result = respBody.result
                        val scores = result?.allScores
                        val aedes = scores?.get("aedes") ?: scores?.get("Aedes")
                        val anopheles = scores?.get("anopheles") ?: scores?.get("Anopheles")
                        val culex = scores?.get("culex") ?: scores?.get("Culex")

                        submissionDao.updateWithRemoteResult(
                            id = sub.id,
                            remoteId = respBody.id,
                            predictedGenus = result?.predictedGenus,
                            confidence = result?.confidence,
                            rawScore = result?.rawScore ?: result?.confidence,
                            isUncertain = result?.isUncertain ?: true,
                            modelVersion = result?.modelVersion ?: "3.0.0",
                            modelStatus = result?.modelStatus ?: "EXPERIMENTAL_NOT_FIELD_VALIDATED",
                            processingTimeMs = result?.processingTimeMs,
                            scoreAedes = aedes,
                            scoreAnopheles = anopheles,
                            scoreCulex = culex
                        )
                        synced++
                    } else {
                        failed++
                        lastError = "Server HTTP ${response.code()}"
                    }
                }
            } catch (e: Exception) {
                failed++
                lastError = e.message
            }
        }

        SyncResult(
            totalPending = unsynced.size,
            syncedCount = synced,
            failedCount = failed,
            errorMessage = lastError
        )
    }
}
