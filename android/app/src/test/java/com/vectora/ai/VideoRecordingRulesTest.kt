package com.vectora.ai

import com.vectora.ai.video.VideoRecordingRules
import org.junit.Assert.*
import org.junit.Test

class VideoRecordingRulesTest {

    @Test
    fun testDurationBoundaries() {
        // 2.99s: reject
        val r299 = VideoRecordingRules.validateDuration(2.99f)
        assertFalse(r299.isValid)
        assertEquals(VideoRecordingRules.ErrorCode.VIDEO_TOO_SHORT, r299.errorCode)

        // 3.00s: accept
        val r300 = VideoRecordingRules.validateDuration(3.00f)
        assertTrue(r300.isValid)
        assertNull(r300.errorCode)

        // 4.00s: accept
        val r400 = VideoRecordingRules.validateDuration(4.00f)
        assertTrue(r400.isValid)
        assertNull(r400.errorCode)

        // 5.00s: accept
        val r500 = VideoRecordingRules.validateDuration(5.00f)
        assertTrue(r500.isValid)
        assertNull(r500.errorCode)

        // 5.01s: reject
        val r501 = VideoRecordingRules.validateDuration(5.01f)
        assertFalse(r501.isValid)
        assertEquals(VideoRecordingRules.ErrorCode.VIDEO_TOO_LONG, r501.errorCode)
    }

    @Test
    fun testManualStopDisabledBeforeThreeSeconds() {
        assertFalse(VideoRecordingRules.canStopManually(0.0f))
        assertFalse(VideoRecordingRules.canStopManually(1.5f))
        assertFalse(VideoRecordingRules.canStopManually(2.99f))
        assertTrue(VideoRecordingRules.canStopManually(3.0f))
        assertTrue(VideoRecordingRules.canStopManually(4.2f))
    }

    @Test
    fun testAutoStopEnforcedAtFiveSeconds() {
        assertFalse(VideoRecordingRules.mustStopAutomatically(4.99f))
        assertTrue(VideoRecordingRules.mustStopAutomatically(5.0f))
        assertTrue(VideoRecordingRules.mustStopAutomatically(5.01f))
    }

    @Test
    fun testInvalidAndZeroDuration() {
        val rZero = VideoRecordingRules.validateDuration(0.0f)
        assertFalse(rZero.isValid)
        assertEquals(VideoRecordingRules.ErrorCode.VIDEO_INVALID_DURATION, rZero.errorCode)

        val rNegative = VideoRecordingRules.validateDuration(-1.0f)
        assertFalse(rNegative.isValid)
        assertEquals(VideoRecordingRules.ErrorCode.VIDEO_INVALID_DURATION, rNegative.errorCode)

        val rNan = VideoRecordingRules.validateDuration(Float.NaN)
        assertFalse(rNan.isValid)
        assertEquals(VideoRecordingRules.ErrorCode.VIDEO_INVALID_DURATION, rNan.errorCode)
    }
}
