package com.vectora.ai.inference

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.graphics.Bitmap
import com.vectora.ai.domain.model.IdentificationResult
import java.nio.FloatBuffer
import java.util.UUID
import kotlin.math.exp

/**
 * ONNX Runtime Mobile classifier for adult mosquito genus identification.
 * Uses EfficientNet-B0 INT8 quantized model.
 */
class OnnxAdultClassifier(context: Context) {

    private val env: OrtEnvironment = OrtEnvironment.getEnvironment()
    private val session: OrtSession

    companion object {
        const val MODEL_FILE = "efficientnet_b0_int8.onnx"
        val CLASSES = listOf("aedes", "anopheles", "culex")
        const val INPUT_SIZE = 224
        val MEAN = floatArrayOf(0.485f, 0.456f, 0.406f)
        val STD = floatArrayOf(0.229f, 0.224f, 0.225f)
        const val CONFIDENCE_THRESHOLD = 0.65f
        const val MODEL_VERSION = "1.0.0"
    }

    init {
        val modelBytes = context.assets.open(MODEL_FILE).readBytes()
        session = env.createSession(modelBytes)
    }

    /**
     * Classify a bitmap image.
     * Returns [IdentificationResult] with genus prediction and confidence.
     */
    fun classify(bitmap: Bitmap, imagePath: String? = null): IdentificationResult {
        val startTime = System.currentTimeMillis()

        // 1. Preprocess: resize and normalize to CHW [1, 3, 224, 224]
        val floatInput = ImagePreprocessor.preprocessFlat(bitmap)

        // 2. Create ONNX tensor [1, 3, 224, 224]
        val inputShape = longArrayOf(1L, 3L, INPUT_SIZE.toLong(), INPUT_SIZE.toLong())
        val floatBuffer = FloatBuffer.wrap(floatInput)
        val inputTensor = OnnxTensor.createTensor(env, floatBuffer, inputShape)

        // 3. Run inference
        val inputName = session.inputNames.iterator().next()
        val results = session.run(mapOf(inputName to inputTensor))

        // 4. Extract logits (shape: [1, 3])
        val outputTensor = results[0].value as Array<*>
        val logits = (outputTensor[0] as FloatArray)

        // 5. Apply softmax
        val scores = softmax(logits)

        // 6. Find max class
        val maxIdx = scores.indices.maxByOrNull { scores[it] } ?: 0
        val maxScore = scores[maxIdx]
        val isUncertain = maxScore < CONFIDENCE_THRESHOLD
        val predictedGenus = if (!isUncertain) CLASSES[maxIdx] else null

        val uncertaintyMessage = when {
            !isUncertain -> null
            maxScore < 0.40f -> "Non-target object detected."
            else -> "Uncertain identification. Manual inspection is advised."
        }

        val processingTimeMs = System.currentTimeMillis() - startTime

        inputTensor.close()
        results.close()

        return IdentificationResult(
            id = UUID.randomUUID().toString(),
            predictedGenus = predictedGenus,
            confidence = maxScore,
            isUncertain = isUncertain,
            uncertaintyMessage = uncertaintyMessage,
            allScores = CLASSES.zip(scores.toList()).toMap(),
            modelVersion = MODEL_VERSION,
            processingTimeMs = processingTimeMs,
            imagePath = imagePath
        )
    }

    /**
     * Numerically stable softmax.
     */
    private fun softmax(logits: FloatArray): FloatArray {
        val maxVal = logits.max()
        val exps = logits.map { exp((it - maxVal).toDouble()).toFloat() }.toFloatArray()
        val sum = exps.sum()
        return FloatArray(exps.size) { exps[it] / sum }
    }

    fun close() {
        session.close()
        env.close()
    }
}
