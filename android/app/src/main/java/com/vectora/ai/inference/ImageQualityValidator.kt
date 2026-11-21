package com.vectora.ai.inference

import android.graphics.Bitmap
import android.graphics.Color
import kotlin.math.abs

/**
 * Validates specimen photograph quality prior to adult mosquito identification.
 *
 * Checks:
 * - Minimum dimensions (100x100)
 * - Luminance / exposure (detects very dark or overexposed images)
 * - Sharpness / blur (detects blurred captures via gradient variance)
 */
object ImageQualityValidator {

    data class QualityCheckResult(
        val isUsable: Boolean,
        val meanLuminance: Float,
        val sharpnessScore: Float,
        val warningMessage: String?
    )

    const val MIN_DIMENSION = 100
    const val MIN_LUMINANCE = 25.0f
    const val MAX_LUMINANCE = 245.0f
    const val MIN_SHARPNESS = 8.0f

    /**
     * Evaluate quality of the specimen bitmap.
     */
    fun evaluate(bitmap: Bitmap): QualityCheckResult {
        if (bitmap.width < MIN_DIMENSION || bitmap.height < MIN_DIMENSION) {
            return QualityCheckResult(
                isUsable = false,
                meanLuminance = 0f,
                sharpnessScore = 0f,
                warningMessage = "Image is too small (${bitmap.width}x${bitmap.height}). Minimum 100x100 required."
            )
        }

        // Subsample for fast evaluation (max 128x128)
        val sampleSize = 128
        val scaled = if (bitmap.width > sampleSize || bitmap.height > sampleSize) {
            Bitmap.createScaledBitmap(bitmap, sampleSize, sampleSize, false)
        } else {
            bitmap
        }

        val w = scaled.width
        val h = scaled.height
        var totalLuminance = 0.0
        val gray = FloatArray(w * h)

        var idx = 0
        for (y in 0 until h) {
            for (x in 0 until w) {
                val p = scaled.getPixel(x, y)
                val lum = 0.299f * Color.red(p) + 0.587f * Color.green(p) + 0.114f * Color.blue(p)
                gray[idx++] = lum
                totalLuminance += lum
            }
        }

        val meanLuminance = (totalLuminance / (w * h)).toFloat()

        // Compute sharpness via gradient energy (horizontal + vertical differences)
        var gradientSum = 0.0
        var count = 0
        for (y in 1 until h - 1) {
            for (x in 1 until w - 1) {
                val center = gray[y * w + x]
                val dx = abs(center - gray[y * w + (x + 1)])
                val dy = abs(center - gray[(y + 1) * w + x])
                gradientSum += (dx + dy)
                count++
            }
        }

        val sharpnessScore = if (count > 0) (gradientSum / count).toFloat() else 0.0f

        if (scaled != bitmap) {
            scaled.recycle()
        }

        val warning = when {
            meanLuminance < MIN_LUMINANCE -> "Photograph is very dark. Ensure specimen is well lit."
            meanLuminance > MAX_LUMINANCE -> "Photograph is overexposed. Reduce glare or flash."
            sharpnessScore < MIN_SHARPNESS -> "Photograph appears blurred. Hold still and refocus on the specimen."
            else -> null
        }

        return QualityCheckResult(
            isUsable = warning == null,
            meanLuminance = meanLuminance,
            sharpnessScore = sharpnessScore,
            warningMessage = warning
        )
    }
}
