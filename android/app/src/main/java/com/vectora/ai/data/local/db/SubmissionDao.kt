package com.vectora.ai.data.local.db

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface SubmissionDao {

    @Query("SELECT * FROM submissions ORDER BY createdAt DESC")
    fun getAllSubmissions(): Flow<List<SubmissionEntity>>

    @Query("SELECT * FROM submissions WHERE id = :id")
    suspend fun getSubmissionById(id: String): SubmissionEntity?

    @Query("SELECT * FROM submissions WHERE type = :type ORDER BY createdAt DESC")
    fun getSubmissionsByType(type: String): Flow<List<SubmissionEntity>>

    @Query("SELECT * FROM submissions WHERE synced = 0 OR status = 'PENDING_UPLOAD' ORDER BY createdAt DESC")
    suspend fun getUnsyncedSubmissions(): List<SubmissionEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(submission: SubmissionEntity)

    @Update
    suspend fun update(submission: SubmissionEntity)

    @Delete
    suspend fun delete(submission: SubmissionEntity)

    @Query("DELETE FROM submissions WHERE id = :id")
    suspend fun deleteById(id: String)

    @Query("UPDATE submissions SET synced = 1, status = 'COMPLETED', remoteId = :remoteId WHERE id = :id")
    suspend fun markSynced(id: String, remoteId: String)

    @Query("""
        UPDATE submissions 
        SET synced = 1,
            status = 'COMPLETED',
            remoteId = :remoteId,
            predictedGenus = :predictedGenus,
            confidence = :confidence,
            rawScore = :rawScore,
            isUncertain = :isUncertain,
            modelVersion = :modelVersion,
            modelStatus = :modelStatus,
            processingTimeMs = :processingTimeMs,
            scoreAedes = :scoreAedes,
            scoreAnopheles = :scoreAnopheles,
            scoreCulex = :scoreCulex
        WHERE id = :id
    """)
    suspend fun updateWithRemoteResult(
        id: String,
        remoteId: String,
        predictedGenus: String?,
        confidence: Float?,
        rawScore: Float?,
        isUncertain: Boolean,
        modelVersion: String,
        modelStatus: String?,
        processingTimeMs: Long?,
        scoreAedes: Float? = null,
        scoreAnopheles: Float? = null,
        scoreCulex: Float? = null
    )

    @Query("UPDATE submissions SET aiExplanation = :explanation WHERE id = :id")
    suspend fun updateAiExplanation(id: String, explanation: String)
}
