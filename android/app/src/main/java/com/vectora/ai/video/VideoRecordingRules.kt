package com.vectora.ai.video

import kotlin.math.round

/**
 * Enforces strict video recording and validation rules for mosquito larvae locomotion.
 *
 * Requirements:
 * - Minimum duration: 3.0 seconds
 * - Maximum duration: 5.0 seconds
 * - Recording can stop manually after 3.0 seconds
 * - Recording must stop automatically at 5.0 seconds
 * - Videos outside [3.0, 5.0] must be rejected
 */
object VideoRecordingRules {

    const val MIN_DURATION_SECONDS: Float = 3.0f
    const val MAX_DURATION_SECONDS: Float = 5.0f

    enum class ErrorCode {
        VIDEO_TOO_SHORT,
        VIDEO_TOO_LONG,
        VIDEO_CORRUPTED,
        VIDEO_INVALID_DURATION
    }

    data class ValidationResult(
        val isValid: Boolean,
        val durationSeconds: Float,
        val errorCode: ErrorCode? = null,
        val message: String? = null
    )

    /**
     * Check if manual stop is permitted given the elapsed time.
     */
    fun canStopManually(elapsedSeconds: Float): Boolean {
        return elapsedSeconds >= MIN_DURATION_SECONDS
    }

    /**
     * Check if recording has reached the hard ceiling and must stop automatically.
     */
    fun mustStopAutomatically(elapsedSeconds: Float): Boolean {
        return elapsedSeconds >= MAX_DURATION_SECONDS
    }

    /**
     * Validate recorded duration against 3.0s – 5.0s boundaries.
     * Rounds to 2 decimal places to match decoded media accuracy.
     */
    fun validateDuration(durationSeconds: Float): ValidationResult {
        if (!durationSeconds.isFinite() || durationSeconds <= 0.0f) {
            return ValidationResult(
                isValid = false,
                durationSeconds = 0.0f,
                errorCode = ErrorCode.VIDEO_INVALID_DURATION,
                message = "Duration cannot be determined."
            )
        }

        val rounded = round(durationSeconds * 100f) / 100f

        return when {
            rounded < MIN_DURATION_SECONDS -> ValidationResult(
                isValid = false,
                durationSeconds = rounded,
                errorCode = ErrorCode.VIDEO_TOO_SHORT,
                message = "The video must be at least 3 seconds (actual: ${rounded}s)."
            )
            rounded > MAX_DURATION_SECONDS -> ValidationResult(
                isValid = false,
                durationSeconds = rounded,
                errorCode = ErrorCode.VIDEO_TOO_LONG,
                message = "The video must not exceed 5 seconds (actual: ${rounded}s)."
            )
            else -> ValidationResult(
                isValid = true,
                durationSeconds = rounded,
                errorCode = null,
                message = null
            )
        }
    }
}
