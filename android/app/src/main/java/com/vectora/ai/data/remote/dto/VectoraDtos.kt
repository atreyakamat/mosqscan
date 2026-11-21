package com.vectora.ai.data.remote.dto

import com.google.gson.annotations.SerializedName

// --- Authentication DTOs ---

data class LoginRequest(
    val email: String,
    val password: String
)

data class RegisterRequest(
    val username: String,
    val email: String,
    val password: String
)

data class UserDto(
    val id: String,
    val email: String,
    val username: String,
    val role: String
)

data class AuthResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String,
    val user: UserDto? = null
)

// --- Adult Mosquito Identification DTOs ---

data class QualityFeedbackDto(
    @SerializedName("blur_score") val blurScore: Float? = null,
    @SerializedName("is_blurry") val isBlurry: Boolean? = null,
    @SerializedName("brightness") val brightness: Float? = null,
    @SerializedName("quality_feedback") val qualityFeedback: String? = null,
    @SerializedName("crop_applied") val cropApplied: Boolean? = null,
    @SerializedName("crop_mode") val cropMode: String? = null,
    @SerializedName("notes") val notes: String? = null,
    @SerializedName("scientific_disclaimer") val scientificDisclaimer: String? = null
)

data class AdultResultDto(
    @SerializedName("predicted_genus") val predictedGenus: String?,
    val confidence: Float?,
    @SerializedName("raw_score") val rawScore: Float?,
    @SerializedName("is_uncertain") val isUncertain: Boolean,
    @SerializedName("uncertainty_message") val uncertaintyMessage: String?,
    @SerializedName("all_scores") val allScores: Map<String, Float>?,
    @SerializedName("model_version") val modelVersion: String,
    @SerializedName("model_status") val modelStatus: String?,
    @SerializedName("model_artifact") val modelArtifact: String,
    @SerializedName("processing_time_ms") val processingTimeMs: Long,
    @SerializedName("quality_feedback") val qualityFeedback: QualityFeedbackDto? = null
)

data class AdultSubmissionResponse(
    val id: String,
    val status: String,
    val type: String,
    @SerializedName("created_at") val createdAt: String,
    val result: AdultResultDto?
)

// --- System & Model Health DTOs ---

data class HealthResponse(
    val status: String,
    val service: String,
    val version: String,
    val environment: String? = null
)

data class ModelHealthResponse(
    val status: String,
    @SerializedName("model_version") val modelVersion: String,
    val artifact: String,
    @SerializedName("checksum_verified") val checksumVerified: Boolean,
    @SerializedName("actual_sha256") val actualSha256: String? = null
)
