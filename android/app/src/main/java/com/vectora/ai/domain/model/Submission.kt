package com.vectora.ai.domain.model

data class Submission(
    val id: String,
    val type: String,              // "adult" or "larvae"
    val imagePath: String?,
    val videoPath: String?,
    val predictedGenus: String?,   // null if uncertain
    val confidence: Float?,
    val isUncertain: Boolean,
    val modelVersion: String,
    val processingTimeMs: Long?,
    val createdAt: Long,
    val synced: Boolean = false,
    val remoteId: String? = null
)
