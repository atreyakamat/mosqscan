package com.vectora.ai.data.local.db

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "submissions")
data class SubmissionEntity(
    @PrimaryKey val id: String,            // UUID
    val type: String,                      // "adult" or "larvae"
    val imagePath: String?,                // Local file path
    val videoPath: String?,
    val predictedGenus: String?,           // null if uncertain
    val confidence: Float?,
    val isUncertain: Boolean,
    val modelVersion: String,
    val processingTimeMs: Long?,
    val createdAt: Long,                   // Unix timestamp
    val synced: Boolean = false,           // Whether synced to backend
    val remoteId: String? = null,          // Backend ID after sync
    val status: String = "COMPLETED",      // "PENDING_UPLOAD", "COMPLETED", "FAILED"
    val rawScore: Float? = null,
    val modelStatus: String? = null,
    val cropX: Float? = null,
    val cropY: Float? = null,
    val cropW: Float? = null,
    val cropH: Float? = null
)
