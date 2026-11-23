package com.vectora.ai.ui.navigation

import java.net.URLEncoder
import java.nio.charset.StandardCharsets

sealed class Screen(val route: String) {
    data object Splash : Screen("splash")
    data object PermissionSetup : Screen("permission_setup")
    data object Main : Screen("main")
    data object Dashboard : Screen("main")
    data object AdultCapture : Screen("adult_capture")
    data object AdultCrop : Screen("adult_crop/{imagePath}") {
        fun createRoute(imagePath: String): String {
            val encoded = URLEncoder.encode(imagePath, StandardCharsets.UTF_8.toString())
            return "adult_crop/$encoded"
        }
    }
    data object AdultUpload : Screen("adult_upload/{submissionId}") {
        fun createRoute(submissionId: String) = "adult_upload/$submissionId"
    }
    data object Result : Screen("result/{submissionId}") {
        fun createRoute(submissionId: String) = "result/$submissionId"
    }
    data object LarvaeCapture : Screen("larvae_capture")
    data object History : Screen("history")
    data object Settings : Screen("settings")
    data object Auth : Screen("auth")
    data object Onboarding : Screen("onboarding")
    data object Assistant : Screen("assistant")
}
