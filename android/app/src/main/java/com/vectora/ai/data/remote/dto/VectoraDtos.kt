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

// --- Local AI Assistant DTOs (Gemma 3:4B) ---

data class AssistantHealthResponse(
    val status: String,
    @SerializedName("ollama_base_url") val ollamaBaseUrl: String,
    @SerializedName("target_model") val targetModel: String,
    @SerializedName("model_loaded") val modelLoaded: Boolean,
    @SerializedName("available_models") val availableModels: List<String> = emptyList(),
    val guardrail: String? = null
)

data class AssistantQueryRequest(
    val prompt: String,
    @SerializedName("system_prompt") val systemPrompt: String? = null,
    val temperature: Float = 0.2f,
    @SerializedName("json_mode") val jsonMode: Boolean = false
)

data class ExplainResultRequest(
    val genus: String,
    @SerializedName("raw_scores") val rawScores: Map<String, Float>? = null,
    @SerializedName("scan_id") val scanId: String? = null,
    @SerializedName("quality_feedback") val qualityFeedback: Map<String, Any>? = null
)

data class AssistantResponse(
    val success: Boolean,
    val response: String,
    @SerializedName("processing_time_seconds") val processingTimeSeconds: Float? = null,
    val model: String? = null,
    val error: String? = null
)

// --- Dashboard & Submissions DTOs ---

data class DashboardStatsDto(
    @SerializedName("total_submissions") val totalSubmissions: Int,
    @SerializedName("adult_submissions") val adultSubmissions: Int,
    @SerializedName("larvae_submissions") val larvaeSubmissions: Int,
    @SerializedName("successful_identifications") val successfulIdentifications: Int,
    @SerializedName("uncertain_identifications") val uncertainIdentifications: Int,
    @SerializedName("failed_submissions") val failedSubmissions: Int
)
