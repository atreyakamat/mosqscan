package com.vectora.ai.inference

import android.graphics.Bitmap
import android.graphics.Color

/**
 * Handles image preprocessing to match backend ImageNet normalization.
 * Input: any Bitmap
 * Output: float array [1, 3, 224, 224] in CHW format, normalized with ImageNet mean/std
 */
object ImagePreprocessor {

    private val MEAN = floatArrayOf(0.485f, 0.456f, 0.406f)
    private val STD = floatArrayOf(0.229f, 0.224f, 0.225f)
    const val INPUT_SIZE = 224

    /**
     * Resize and normalize a bitmap to [1, 3, 224, 224] float array.
     */
    fun preprocess(bitmap: Bitmap): Array<Array<Array<FloatArray>>> {
        val resized = Bitmap.createScaledBitmap(bitmap, INPUT_SIZE, INPUT_SIZE, true)

        // CHW layout: [batch=1, channels=3, height=224, width=224]
        val result = Array(1) { Array(3) { Array(INPUT_SIZE) { FloatArray(INPUT_SIZE) } } }

        for (y in 0 until INPUT_SIZE) {
            for (x in 0 until INPUT_SIZE) {
                val pixel = resized.getPixel(x, y)
                val r = Color.red(pixel) / 255.0f
                val g = Color.green(pixel) / 255.0f
                val b = Color.blue(pixel) / 255.0f

                result[0][0][y][x] = (r - MEAN[0]) / STD[0]
                result[0][1][y][x] = (g - MEAN[1]) / STD[1]
                result[0][2][y][x] = (b - MEAN[2]) / STD[2]
            }
        }

        if (resized != bitmap) resized.recycle()

        return result
    }

    /**
     * Flatten the CHW array into a 1D float array for ONNX Runtime input.
     */
    fun preprocessFlat(bitmap: Bitmap): FloatArray {
        val resized = Bitmap.createScaledBitmap(bitmap, INPUT_SIZE, INPUT_SIZE, true)
        val floats = FloatArray(3 * INPUT_SIZE * INPUT_SIZE)
        var idx = 0

        // R channel
        for (y in 0 until INPUT_SIZE) {
            for (x in 0 until INPUT_SIZE) {
                val pixel = resized.getPixel(x, y)
                floats[idx++] = (Color.red(pixel) / 255.0f - MEAN[0]) / STD[0]
            }
        }
        // G channel
        for (y in 0 until INPUT_SIZE) {
            for (x in 0 until INPUT_SIZE) {
                val pixel = resized.getPixel(x, y)
                floats[idx++] = (Color.green(pixel) / 255.0f - MEAN[1]) / STD[1]
            }
        }
        // B channel
        for (y in 0 until INPUT_SIZE) {
            for (x in 0 until INPUT_SIZE) {
                val pixel = resized.getPixel(x, y)
                floats[idx++] = (Color.blue(pixel) / 255.0f - MEAN[2]) / STD[2]
            }
        }

        if (resized != bitmap) resized.recycle()
        return floats
    }
}
