package com.vectora.ai.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.vectora.ai.data.local.db.SubmissionDao
import com.vectora.ai.data.local.keystore.KeystoreManager
import com.vectora.ai.data.remote.ServerClientManager
import com.vectora.ai.ui.screens.*
import java.net.URLDecoder
import java.nio.charset.StandardCharsets

@Composable
fun VectoraNavGraph(
    navController: NavHostController = rememberNavController(),
    submissionDao: SubmissionDao? = null
) {
    val context = LocalContext.current
    val keystore = remember { KeystoreManager(context) }
    val serverClientManager = remember { ServerClientManager(context, keystore) }

    val activeDao = submissionDao ?: remember {
        androidx.room.Room.databaseBuilder(
            context,
            com.vectora.ai.data.local.db.AppDatabase::class.java,
            "vectora_ai.db"
        ).fallbackToDestructiveMigration().build().submissionDao()
    }

    NavHost(
        navController = navController,
        startDestination = Screen.Dashboard.route
    ) {
        composable(Screen.Dashboard.route) {
            DashboardScreen(
                submissionDao = activeDao,
                serverClientManager = serverClientManager,
                onNavigateToAdultCapture = { navController.navigate(Screen.AdultCapture.route) },
                onNavigateToLarvaeCapture = { navController.navigate(Screen.LarvaeCapture.route) },
                onNavigateToHistory = { navController.navigate(Screen.History.route) },
                onNavigateToSettings = { navController.navigate(Screen.Settings.route) }
            )
        }

        composable(Screen.AdultCapture.route) {
            AdultCaptureScreen(
                cacheDir = context.cacheDir,
                onBack = { navController.popBackStack() },
                onPhotoSelected = { path ->
                    navController.navigate(Screen.AdultCrop.createRoute(path))
                }
            )
        }

        composable(
            route = Screen.AdultCrop.route,
            arguments = listOf(navArgument("imagePath") { type = NavType.StringType })
        ) { backStackEntry ->
            val rawPath = backStackEntry.arguments?.getString("imagePath") ?: ""
            val imagePath = try {
                URLDecoder.decode(rawPath, StandardCharsets.UTF_8.toString())
            } catch (_: Exception) {
                rawPath
            }
            AdultCropScreen(
                imagePath = imagePath,
                submissionDao = activeDao,
                cacheDir = context.cacheDir,
                onRetake = { navController.popBackStack() },
                onConfirmCrop = { subId ->
                    navController.navigate(Screen.AdultUpload.createRoute(subId))
                }
            )
        }

        composable(
            route = Screen.AdultUpload.route,
            arguments = listOf(navArgument("submissionId") { type = NavType.StringType })
        ) { backStackEntry ->
            val subId = backStackEntry.arguments?.getString("submissionId") ?: ""
            AdultUploadScreen(
                submissionId = subId,
                submissionDao = activeDao,
                serverClientManager = serverClientManager,
                onUploadSuccess = { id ->
                    navController.navigate(Screen.Result.createRoute(id)) {
                        popUpTo(Screen.Dashboard.route)
                    }
                },
                onCancelToDashboard = {
                    navController.navigate(Screen.Dashboard.route) {
                        popUpTo(Screen.Dashboard.route) { inclusive = true }
                    }
                },
                onNavigateToAuth = {
                    navController.navigate(Screen.Auth.route)
                }
            )
        }

        composable(Screen.LarvaeCapture.route) {
            LarvaeCaptureScreen(
                submissionDao = activeDao,
                onBack = { navController.popBackStack() },
                onVideoRecorded = { id ->
                    navController.navigate(Screen.Result.createRoute(id)) {
                        popUpTo(Screen.Dashboard.route)
                    }
                }
            )
        }

        composable(
            route = Screen.Result.route,
            arguments = listOf(navArgument("submissionId") { type = NavType.StringType })
        ) { backStackEntry ->
            val subId = backStackEntry.arguments?.getString("submissionId") ?: ""
            ResultScreen(
                submissionId = subId,
                submissionDao = activeDao,
                onBackToDashboard = {
                    navController.navigate(Screen.Dashboard.route) {
                        popUpTo(Screen.Dashboard.route) { inclusive = true }
                    }
                },
                onNavigateToHistory = {
                    navController.navigate(Screen.History.route) {
                        popUpTo(Screen.Dashboard.route)
                    }
                },
                onRetryUpload = { id ->
                    navController.navigate(Screen.AdultUpload.createRoute(id))
                }
            )
        }

        composable(Screen.History.route) {
            HistoryScreen(
                submissionDao = activeDao,
                onBack = { navController.popBackStack() },
                onSelectSubmission = { id ->
                    navController.navigate(Screen.Result.createRoute(id))
                }
            )
        }

        composable(Screen.Settings.route) {
            SettingsScreen(
                onBack = { navController.popBackStack() },
                onNavigateToAuth = { navController.navigate(Screen.Auth.route) },
                keystoreManager = keystore,
                serverClientManager = serverClientManager
            )
        }

        composable(Screen.Auth.route) {
            AuthScreen(
                keystoreManager = keystore,
                serverClientManager = serverClientManager,
                onBack = { navController.popBackStack() },
                onAuthSuccess = { navController.popBackStack() }
            )
        }
    }
}
