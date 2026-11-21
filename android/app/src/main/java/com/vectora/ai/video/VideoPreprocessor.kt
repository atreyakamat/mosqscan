package com.vectora.ai.video

import android.media.MediaMetadataRetriever
import java.io.File

/**
 * Preprocessing and validation utility for larvae video clips.
 */
object VideoPreprocessor {

    /**
     * Inspect a recorded video file on disk, decode its duration via MediaMetadataRetriever,
     * and validate against strict 3.0s - 5.0s boundaries.
     */
    fun validateVideoFile(file: File): VideoRecordingRules.ValidationResult {
        if (!file.exists() || file.length() == 0L) {
            return VideoRecordingRules.ValidationResult(
                isValid = false,
                durationSeconds = 0.0f,
                errorCode = VideoRecordingRules.ErrorCode.VIDEO_CORRUPTED,
                message = "Video file does not exist or is empty."
            )
        }

        val retriever = MediaMetadataRetriever()
        return try {
            retriever.setDataSource(file.absolutePath)
            val durationStr = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)
            val durationMs = durationStr?.toLongOrNull() ?: 0L

            if (durationMs <= 0L) {
                VideoRecordingRules.ValidationResult(
                    isValid = false,
                    durationSeconds = 0.0f,
                    errorCode = VideoRecordingRules.ErrorCode.VIDEO_INVALID_DURATION,
                    message = "Could not decode media duration."
                )
            } else {
                val durationSec = durationMs / 1000.0f
                VideoRecordingRules.validateDuration(durationSec)
            }
        } catch (e: Exception) {
            VideoRecordingRules.ValidationResult(
                isValid = false,
                durationSeconds = 0.0f,
                errorCode = VideoRecordingRules.ErrorCode.VIDEO_CORRUPTED,
                message = "Failed to inspect video: ${e.message}"
            )
        } finally {
            try {
                retriever.release()
            } catch (_: Exception) {
            }
        }
    }
}
