package com.vectora.ai.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vectora.ai.data.local.db.SubmissionDao
import com.vectora.ai.data.local.db.SubmissionEntity
import com.vectora.ai.data.remote.ServerClientManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AdultUploadScreen(
    submissionId: String,
    submissionDao: SubmissionDao,
    serverClientManager: ServerClientManager,
    onUploadSuccess: (submissionId: String) -> Unit,
    onCancelToDashboard: () -> Unit,
    onNavigateToAuth: () -> Unit = {}
) {
    val coroutineScope = rememberCoroutineScope()

    var submission by remember { mutableStateOf<SubmissionEntity?>(null) }
    var uploadStatusMessage by remember { mutableStateOf("Initializing upload...") }
    var uploadProgress by remember { mutableFloatStateOf(0.1f) }
    var isUploading by remember { mutableStateOf(false) }
    var uploadError by remember { mutableStateOf<String?>(null) }

    fun startUpload() {
        if (isUploading) return
        isUploading = true
        uploadError = null
        uploadProgress = 0.15f
        uploadStatusMessage = "Connecting to Vectora AI Server (${serverClientManager.baseUrl})..."

        coroutineScope.launch {
            try {
                val sub = withContext(Dispatchers.IO) {
                    submissionDao.getSubmissionById(submissionId)
                }
                if (sub == null || sub.imagePath == null) {
                    uploadError = "Submission record or image not found locally."
                    isUploading = false
                    return@launch
                }
                submission = sub

                val file = File(sub.imagePath)
                if (!file.exists()) {
                    uploadError = "Specimen photograph missing from device storage."
                    isUploading = false
                    return@launch
                }

                uploadProgress = 0.35f
                uploadStatusMessage = "Packaging high-resolution photograph (${file.length() / 1024} KB)..."
                delay(200)

                val requestFile = file.asRequestBody("image/jpeg".toMediaTypeOrNull())
                val body = MultipartBody.Part.createFormData("file", file.name, requestFile)

                val cropX = sub.cropX?.toString()?.toRequestBody("text/plain".toMediaTypeOrNull())
                val cropY = sub.cropY?.toString()?.toRequestBody("text/plain".toMediaTypeOrNull())
                val cropW = sub.cropW?.toString()?.toRequestBody("text/plain".toMediaTypeOrNull())
                val cropH = sub.cropH?.toString()?.toRequestBody("text/plain".toMediaTypeOrNull())

                uploadProgress = 0.60f
                uploadStatusMessage = "Uploading image and crop parameters to i7 host..."

                val service = serverClientManager.getService()
                val response = withContext(Dispatchers.IO) {
                    service.submitAdult(body, cropX, cropY, cropW, cropH)
                }

                if (response.isSuccessful && response.body() != null) {
                    uploadProgress = 0.90f
                    uploadStatusMessage = "Model inference completed on i7 CPU. Synchronizing result..."

                    val respBody = response.body()!!
                    val result = respBody.result
                    val scores = result?.allScores
                    val scoreAedes = scores?.get("aedes") ?: scores?.get("Aedes")
                    val scoreAnopheles = scores?.get("anopheles") ?: scores?.get("Anopheles")
                    val scoreCulex = scores?.get("culex") ?: scores?.get("Culex")

                    withContext(Dispatchers.IO) {
                        submissionDao.updateWithRemoteResult(
                            id = sub.id,
                            remoteId = respBody.id,
                            predictedGenus = result?.predictedGenus,
                            confidence = result?.confidence,
                            rawScore = result?.rawScore ?: result?.confidence,
                            isUncertain = result?.isUncertain ?: true,
                            modelVersion = result?.modelVersion ?: "3.0.0",
                            modelStatus = result?.modelStatus ?: "EXPERIMENTAL_NOT_FIELD_VALIDATED",
                            processingTimeMs = result?.processingTimeMs,
                            scoreAedes = scoreAedes,
                            scoreAnopheles = scoreAnopheles,
                            scoreCulex = scoreCulex
                        )
                    }

                    uploadProgress = 1.0f
                    uploadStatusMessage = "Complete!"
                    delay(300)
                    isUploading = false
                    onUploadSuccess(submissionId)
                } else {
                    val code = response.code()
                    val errBody = response.errorBody()?.string() ?: response.message()
                    uploadError = "Server rejected upload (HTTP $code): $errBody"
                    isUploading = false
                }
            } catch (e: Exception) {
                uploadError = "Connection failed: ${e.message ?: "Server unreachable"}. Photograph is safely saved locally."
                isUploading = false
            }
        }
    }

    LaunchedEffect(submissionId) {
        startUpload()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Server Inference Upload", fontSize = 18.sp, fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onCancelToDashboard) {
                        Icon(Icons.Default.Close, contentDescription = "Cancel")
                    }
                }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            if (uploadError != null) {
                // Failure / Offline state
                Icon(
                    Icons.Default.CloudOff,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.error,
                    modifier = Modifier.size(64.dp)
                )
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    "Upload Failed / Server Unavailable",
                    fontWeight = FontWeight.Bold,
                    fontSize = 18.sp,
                    color = MaterialTheme.colorScheme.error
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    uploadError!!,
                    fontSize = 13.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.height(16.dp))

                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(
                            "Status: PENDING_UPLOAD",
                            fontWeight = FontWeight.Bold,
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.primary
                        )
                        Text(
                            "Your photograph and crop parameters have been securely stored in the local Room database. No prediction will be fabricated without server response. You can retry once connectivity is restored.",
                            fontSize = 11.sp
                        )
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))

                val isAuthError = uploadError?.contains("401") == true || uploadError?.contains("UNAUTHORIZED") == true

                if (isAuthError) {
                    Button(
                        onClick = onNavigateToAuth,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Default.Lock, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Sign In to Authorize Upload")
                    }
                    Spacer(modifier = Modifier.height(10.dp))
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedButton(
                        onClick = onCancelToDashboard,
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Save & Exit")
                    }

                    Button(
                        onClick = { startUpload() },
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Retry Upload")
                    }
                }
            } else {
                // In-progress State
                Icon(
                    Icons.Default.CloudUpload,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(64.dp)
                )
                Spacer(modifier = Modifier.height(24.dp))

                Text(
                    "Processing Remote AI Inference",
                    fontWeight = FontWeight.Bold,
                    fontSize = 18.sp
                )
                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    uploadStatusMessage,
                    fontSize = 13.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.height(24.dp))

                LinearProgressIndicator(
                    progress = { uploadProgress },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(8.dp)
                )
                Spacer(modifier = Modifier.height(16.dp))

                Text(
                    "Target Host: Intel Core i7-2600 (CPU FP32 Exp B Candidate)\nServer: ${serverClientManager.baseUrl}",
                    fontSize = 11.sp,
                    color = Color.Gray
                )
            }
        }
    }
}
