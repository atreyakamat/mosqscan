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
        startDestination = Screen.Splash.route
    ) {
        // Startup Screen: Minimal splash screen with Vectora AI logo and name
        composable(Screen.Splash.route) {
            SplashScreen(
                onNavigateNext = {
                    val nextRoute = if (serverClientManager.isPermissionSetupCompleted) {
                        Screen.Main.route
                    } else {
                        Screen.PermissionSetup.route
                    }
                    navController.navigate(nextRoute) {
                        popUpTo(Screen.Splash.route) { inclusive = true }
                    }
                }
            )
        }

        // Permission Setup Screen
        composable(Screen.PermissionSetup.route) {
            PermissionScreen(
                serverClientManager = serverClientManager,
                onContinue = {
                    navController.navigate(Screen.Main.route) {
                        popUpTo(Screen.PermissionSetup.route) { inclusive = true }
                    }
                }
            )
        }

        // Main Screen: Exactly two options (Adult Mosquito and Mosquito Larvae)
        composable(Screen.Main.route) {
            MainScreen(
                onNavigateToAdultCapture = { navController.navigate(Screen.AdultCapture.route) },
                onNavigateToLarvaeCapture = { navController.navigate(Screen.LarvaeCapture.route) },
                onNavigateToSettings = { navController.navigate(Screen.Settings.route) }
            )
        }

        // Adult Specimen Capture Screen (CameraX + Photo Picker)
        composable(Screen.AdultCapture.route) {
            AdultCaptureScreen(
                cacheDir = context.cacheDir,
                onBack = { navController.popBackStack() },
                onPhotoSelected = { path ->
                    navController.navigate(Screen.AdultCrop.createRoute(path))
                }
            )
        }

        // Adult Specimen Manual Crop Screen
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

        // Adult Specimen Inference Upload Screen
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
                        popUpTo(Screen.Main.route)
                    }
                },
                onCancelToDashboard = {
                    navController.navigate(Screen.Main.route) {
                        popUpTo(Screen.Main.route) { inclusive = true }
                    }
                },
                onNavigateToAuth = {
                    navController.navigate(Screen.Auth.route)
                }
            )
        }

        // Mosquito Larvae Capture Screen (Strict 3-5s limit, research-only)
        composable(Screen.LarvaeCapture.route) {
            LarvaeCaptureScreen(
                submissionDao = activeDao,
                onBack = { navController.popBackStack() },
                onVideoRecorded = { id ->
                    navController.navigate(Screen.Result.createRoute(id)) {
                        popUpTo(Screen.Main.route)
                    }
                }
            )
        }

        // Minimal Result Screen
        composable(
            route = Screen.Result.route,
            arguments = listOf(navArgument("submissionId") { type = NavType.StringType })
        ) { backStackEntry ->
            val subId = backStackEntry.arguments?.getString("submissionId") ?: ""
            ResultScreen(
                submissionId = subId,
                submissionDao = activeDao,
                serverClientManager = serverClientManager,
                onBackToDashboard = {
                    navController.navigate(Screen.Main.route) {
                        popUpTo(Screen.Main.route) { inclusive = true }
                    }
                },
                onNavigateToHistory = null,
                onRetryUpload = { id ->
                    navController.navigate(Screen.AdultUpload.createRoute(id))
                }
            )
        }

        // Settings Screen
        composable(Screen.Settings.route) {
            SettingsScreen(
                onBack = { navController.popBackStack() },
                onNavigateToAuth = { navController.navigate(Screen.Auth.route) },
                onNavigateToOnboarding = { navController.navigate(Screen.PermissionSetup.route) },
                keystoreManager = keystore,
                serverClientManager = serverClientManager,
                submissionDao = activeDao
            )
        }

        // Authentication Screen
        composable(Screen.Auth.route) {
            AuthScreen(
                keystoreManager = keystore,
                serverClientManager = serverClientManager,
                onBack = { navController.popBackStack() },
                onAuthSuccess = { navController.popBackStack() }
            )
        }

        // History Screen (accessible if needed)
        composable(Screen.History.route) {
            HistoryScreen(
                submissionDao = activeDao,
                onBack = { navController.popBackStack() },
                onSelectSubmission = { id ->
                    navController.navigate(Screen.Result.createRoute(id))
                }
            )
        }
    }
}
