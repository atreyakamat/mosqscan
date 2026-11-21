package com.vectora.ai

import android.graphics.Bitmap
import com.vectora.ai.inference.ImageQualityValidator
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import io.mockk.every
import io.mockk.mockk
import io.mockk.mockkStatic

class ImageQualityValidatorTest {

    @Test
    fun testSmallDimensionsRejected() {
        val bitmap = mockk<Bitmap>()
        every { bitmap.width } returns 80
        every { bitmap.height } returns 80

        val result = ImageQualityValidator.evaluate(bitmap)
        assertFalse(result.isUsable)
        assertNotNull(result.warningMessage)
        assertTrue(result.warningMessage!!.contains("too small"))
    }
}
