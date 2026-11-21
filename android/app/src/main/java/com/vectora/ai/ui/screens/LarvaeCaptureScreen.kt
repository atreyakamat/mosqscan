package com.vectora.ai.ui.screens

import android.util.Log
import androidx.camera.core.CameraSelector
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.vectora.ai.data.local.db.SubmissionDao
import com.vectora.ai.data.local.db.SubmissionEntity
import com.vectora.ai.video.VideoRecordingRules
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.UUID

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LarvaeCaptureScreen(
    submissionDao: SubmissionDao,
    onBack: () -> Unit,
    onVideoRecorded: (submissionId: String) -> Unit
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val coroutineScope = rememberCoroutineScope()
    var isRecording by remember { mutableStateOf(false) }
    var elapsedSeconds by remember { mutableStateOf(0.0f) }
    var recordedDuration by remember { mutableStateOf<Float?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var isSaving by remember { mutableStateOf(false) }
    var cameraAvailable by remember { mutableStateOf(true) }

    // Recording timer with strict 5-second automatic stop
    LaunchedEffect(isRecording) {
        if (isRecording) {
            elapsedSeconds = 0.0f
            errorMessage = null
            while (isRecording && elapsedSeconds < VideoRecordingRules.MAX_DURATION_SECONDS) {
                delay(100)
                elapsedSeconds += 0.1f
                if (VideoRecordingRules.mustStopAutomatically(elapsedSeconds)) {
                    // Strict auto-stop at 5.0 seconds
                    elapsedSeconds = VideoRecordingRules.MAX_DURATION_SECONDS
                    isRecording = false
                    recordedDuration = VideoRecordingRules.MAX_DURATION_SECONDS
                    break
                }
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Larvae Video Capture", fontSize = 18.sp, fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(Color.Black)
        ) {
            // CameraX Preview with graceful fallback
            if (cameraAvailable) {
                AndroidView(
                    factory = { ctx ->
                        val previewView = PreviewView(ctx)
                        val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)
                        cameraProviderFuture.addListener({
                            try {
                                val cameraProvider = cameraProviderFuture.get()
                                val preview = Preview.Builder().build().also {
                                    it.setSurfaceProvider(previewView.surfaceProvider)
                                }
                                val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
                                cameraProvider.unbindAll()
                                cameraProvider.bindToLifecycle(
                                    lifecycleOwner,
                                    cameraSelector,
                                    preview
                                )
                            } catch (e: Exception) {
                                Log.w("LarvaeCapture", "Camera preview unavailable: ${e.message}")
                                cameraAvailable = false
                            }
                        }, ContextCompat.getMainExecutor(ctx))
                        previewView
                    },
                    modifier = Modifier.fillMaxSize()
                )
            }

            // Meniscus Alignment Guide
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .align(Alignment.Center),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // Water Meniscus Horizontal Alignment Line
                Box(
                    modifier = Modifier
                        .fillMaxWidth(0.85f)
                        .height(2.dp)
                        .background(Color.Cyan.copy(alpha = 0.8f))
                )
                Text(
                    "Align water meniscus along this line",
                    color = Color.Cyan.copy(alpha = 0.8f),
                    fontSize = 11.sp,
                    modifier = Modifier.padding(top = 4.dp)
                )

                Spacer(modifier = Modifier.height(32.dp))

                // Larvae Observation Box
                Box(
                    modifier = Modifier
                        .size(260.dp, 180.dp)
                        .border(1.dp, Color.White.copy(alpha = 0.5f), MaterialTheme.shapes.small)
                ) {
                    Text(
                        "Subsurface Larvae Observation Area",
                        color = Color.White.copy(alpha = 0.6f),
                        fontSize = 10.sp,
                        modifier = Modifier
                            .align(Alignment.BottomCenter)
                            .padding(6.dp)
                    )
                }
            }

            // Top Status & Timer
            Row(
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .padding(top = 16.dp)
                    .background(Color.Black.copy(alpha = 0.7f), MaterialTheme.shapes.medium)
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                if (isRecording) {
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .background(Color.Red, CircleShape)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        String.format("REC %.1fs / 5.0s", elapsedSeconds),
                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        fontSize = 14.sp
                    )
                } else if (recordedDuration != null) {
                    Text(
                        String.format("Recorded: %.1fs (Target: 3.0s – 5.0s)", recordedDuration),
                        color = Color.White,
                        fontSize = 13.sp
                    )
                } else {
                    Text(
                        "Duration limit: 3.0s – 5.0s strictly",
                        color = Color.White.copy(alpha = 0.8f),
                        fontSize = 12.sp
                    )
                }
            }

            // Error display
            errorMessage?.let { error ->
                Surface(
                    color = MaterialTheme.colorScheme.errorContainer,
                    shape = MaterialTheme.shapes.small,
                    modifier = Modifier
                        .align(Alignment.TopCenter)
                        .padding(top = 64.dp, start = 16.dp, end = 16.dp)
                ) {
                    Text(
                        error,
                        color = MaterialTheme.colorScheme.onErrorContainer,
                        fontSize = 12.sp,
                        modifier = Modifier.padding(10.dp)
                    )
                }
            }

            // Bottom Controls
            Column(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .fillMaxWidth()
                    .background(Color.Black.copy(alpha = 0.7f))
                    .padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                if (recordedDuration != null) {
                    // Review mode
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceEvenly
                    ) {
                        OutlinedButton(
                            onClick = {
                                recordedDuration = null
                                elapsedSeconds = 0.0f
                                errorMessage = null
                            },
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White)
                        ) {
                            Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Retake")
                        }

                        Button(
                            onClick = {
                                val duration = recordedDuration ?: 0.0f
                                val validation = VideoRecordingRules.validateDuration(duration)
                                if (!validation.isValid) {
                                    errorMessage = validation.message ?: "Video duration invalid."
                                    return@Button
                                }

                                isSaving = true
                                coroutineScope.launch {
                                    val subId = UUID.randomUUID().toString()
                                    val entity = SubmissionEntity(
                                        id = subId,
                                        type = "larvae",
                                        imagePath = null,
                                        videoPath = "larvae_$subId.mp4",
                                        predictedGenus = null, // Larvae unvalidated
                                        confidence = null,
                                        isUncertain = true,
                                        modelVersion = "1.0.0",
                                        processingTimeMs = null,
                                        createdAt = System.currentTimeMillis(),
                                        synced = false
                                    )
                                    withContext(Dispatchers.IO) {
                                        submissionDao.insert(entity)
                                    }
                                    isSaving = false
                                    onVideoRecorded(subId)
                                }
                            },
                            enabled = !isSaving,
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                        ) {
                            Text(if (isSaving) "Saving..." else "Submit Clip")
                            Spacer(modifier = Modifier.width(6.dp))
                            Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(16.dp))
                        }
                    }
                } else if (isRecording) {
                    // Recording active: Stop button enabled only after 3.0s!
                    val canStopManually = VideoRecordingRules.canStopManually(elapsedSeconds)

                    Button(
                        onClick = {
                            if (canStopManually) {
                                isRecording = false
                                recordedDuration = elapsedSeconds
                            }
                        },
                        enabled = canStopManually,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = if (canStopManually) Color.Red else Color.Gray
                        ),
                        modifier = Modifier.size(72.dp),
                        shape = CircleShape
                    ) {
                        Box(
                            modifier = Modifier
                                .size(24.dp)
                                .background(Color.White, MaterialTheme.shapes.extraSmall)
                        )
                    }

                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        if (canStopManually) "Tap to stop recording (or auto-stops at 5s)" else "Recording... Min 3s required to stop",
                        color = Color.White,
                        fontSize = 11.sp
                    )
                } else {
                    // Ready to record
                    IconButton(
                        onClick = {
                            isRecording = true
                        },
                        modifier = Modifier
                            .size(72.dp)
                            .background(Color.Red, CircleShape)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(28.dp)
                                .background(Color.White, CircleShape)
                        )
                    }

                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "Tap to start 3–5s recording",
                        color = Color.White.copy(alpha = 0.8f),
                        fontSize = 12.sp
                    )
                }
            }
        }
    }
}
