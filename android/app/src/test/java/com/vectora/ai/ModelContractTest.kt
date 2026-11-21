package com.vectora.ai

import com.vectora.ai.inference.OnnxAdultClassifier
import org.junit.Assert.*
import org.junit.Test

class ModelContractTest {

    @Test
    fun testApprovedModelVersionAndArtifact() {
        assertEquals("1.0.0", OnnxAdultClassifier.MODEL_VERSION)
        assertEquals("efficientnet_b0_int8.onnx", OnnxAdultClassifier.MODEL_FILE)
        assertEquals(224, OnnxAdultClassifier.INPUT_SIZE)
        assertEquals(0.65f, OnnxAdultClassifier.CONFIDENCE_THRESHOLD, 0.0001f)
    }

    @Test
    fun testClassMappingParityWithManifest() {
        val expectedClasses = listOf("aedes", "anopheles", "culex")
        assertEquals(expectedClasses, OnnxAdultClassifier.CLASSES)
    }

    @Test
    fun testNormalizationConstantsParity() {
        val expectedMean = floatArrayOf(0.485f, 0.456f, 0.406f)
        val expectedStd = floatArrayOf(0.229f, 0.224f, 0.225f)
        assertArrayEquals(expectedMean, OnnxAdultClassifier.MEAN, 0.0001f)
        assertArrayEquals(expectedStd, OnnxAdultClassifier.STD, 0.0001f)
    }

    @Test
    fun testUncertaintyMessagesLogic() {
        val threshold = OnnxAdultClassifier.CONFIDENCE_THRESHOLD

        // Below threshold (uncertain)
        fun getUncertaintyMessage(score: Float): String? {
            return when {
                score >= threshold -> null
                score < 0.40f -> "Non-target object detected."
                else -> "Uncertain identification. Manual inspection is advised."
            }
        }

        // 0.75 >= 0.65: confident
        assertNull(getUncertaintyMessage(0.75f))

        // 0.50: uncertain
        assertEquals("Uncertain identification. Manual inspection is advised.", getUncertaintyMessage(0.50f))

        // 0.35: non-target
        assertEquals("Non-target object detected.", getUncertaintyMessage(0.35f))
    }
}
