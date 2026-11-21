package com.vectora.ai.domain.model

data class IdentificationResult(
    val id: String,
    val predictedGenus: String?,   // null if uncertain
    val confidence: Float,
    val isUncertain: Boolean,
    val uncertaintyMessage: String? = null,
    val allScores: Map<String, Float>,
    val modelVersion: String = "1.0.0",
    val processingTimeMs: Long,
    val imagePath: String? = null,
    val videoPath: String? = null
)
