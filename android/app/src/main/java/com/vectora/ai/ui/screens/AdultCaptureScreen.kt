package com.vectora.ai.ui.screens

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.util.Log
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.Camera
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
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
import com.vectora.ai.inference.ImageQualityValidator
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.util.UUID

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AdultCaptureScreen(
    cacheDir: File,
    onBack: () -> Unit,
    onPhotoSelected: (imagePath: String) -> Unit
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val coroutineScope = rememberCoroutineScope()

    var flashMode by remember { mutableIntStateOf(ImageCapture.FLASH_MODE_OFF) }
    var isCapturing by remember { mutableStateOf(false) }
    var qualityWarning by remember { mutableStateOf<String?>(null) }
    var cameraAvailable by remember { mutableStateOf(true) }
    var imageCapture: ImageCapture? by remember { mutableStateOf(null) }
    var cameraControl: Camera? by remember { mutableStateOf(null) }

    // Android Photo Picker launcher for gallery uploads
    val photoPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia()
    ) { uri: Uri? ->
        if (uri != null) {
            coroutineScope.launch {
                try {
                    val destFile = File(cacheDir, "gallery_${UUID.randomUUID()}.jpg")
                    withContext(Dispatchers.IO) {
                        context.contentResolver.openInputStream(uri)?.use { input ->
                            FileOutputStream(destFile).use { output ->
                                input.copyTo(output)
                            }
                        }
                    }
                    onPhotoSelected(destFile.absolutePath)
                } catch (e: Exception) {
                    qualityWarning = "Error loading from gallery: ${e.message}"
                }
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Adult Specimen Capture", fontSize = 18.sp, fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    // Flash Toggle
                    IconButton(onClick = {
                        flashMode = when (flashMode) {
                            ImageCapture.FLASH_MODE_OFF -> ImageCapture.FLASH_MODE_ON
                            ImageCapture.FLASH_MODE_ON -> ImageCapture.FLASH_MODE_AUTO
                            else -> ImageCapture.FLASH_MODE_OFF
                        }
                        imageCapture?.flashMode = flashMode
                    }) {
                        Icon(
                            when (flashMode) {
                                ImageCapture.FLASH_MODE_ON -> Icons.Default.FlashOn
                                ImageCapture.FLASH_MODE_AUTO -> Icons.Default.FlashAuto
                                else -> Icons.Default.FlashOff
                            },
                            contentDescription = "Flash Toggle"
                        )
                    }
                    // Gallery Upload Action
                    IconButton(onClick = {
                        photoPickerLauncher.launch(
                            PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                        )
                    }) {
                        Icon(Icons.Default.PhotoLibrary, contentDescription = "Select from Gallery")
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
            // CameraX Preview
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
                                val capture = ImageCapture.Builder()
                                    .setCaptureMode(ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY)
                                    .setFlashMode(flashMode)
                                    .build()
                                imageCapture = capture

                                val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
                                cameraProvider.unbindAll()
                                cameraControl = cameraProvider.bindToLifecycle(
                                    lifecycleOwner,
                                    cameraSelector,
                                    preview,
                                    capture
                                )
                            } catch (e: Exception) {
                                Log.w("AdultCapture", "Camera preview unavailable: ${e.message}")
                                cameraAvailable = false
                            }
                        }, ContextCompat.getMainExecutor(ctx))
                        previewView
                    },
                    modifier = Modifier.fillMaxSize()
                )
            } else {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(Icons.Default.CameraAlt, contentDescription = null, tint = Color.Gray, modifier = Modifier.size(64.dp))
                        Spacer(modifier = Modifier.height(16.dp))
                        Text("Camera preview unavailable on this device", color = Color.White)
                        Spacer(modifier = Modifier.height(8.dp))
                        Button(onClick = {
                            photoPickerLauncher.launch(
                                PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                            )
                        }) {
                            Text("Select Photograph from Gallery")
                        }
                    }
                }
            }

            // Specimen Viewfinder Framing Guide
            Box(
                modifier = Modifier
                    .size(280.dp)
                    .align(Alignment.Center)
                    .border(2.dp, Color.White.copy(alpha = 0.75f), MaterialTheme.shapes.medium)
            ) {
                Text(
                    "Center mosquito specimen inside guide\n(Manual crop available on next screen)",
                    color = Color.White.copy(alpha = 0.9f),
                    fontSize = 11.sp,
                    lineHeight = 14.sp,
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .padding(8.dp)
                )
            }

            // Quality feedback / warning banner
            qualityWarning?.let { warning ->
                Surface(
                    color = MaterialTheme.colorScheme.errorContainer,
                    shape = MaterialTheme.shapes.small,
                    modifier = Modifier
                        .align(Alignment.TopCenter)
                        .padding(top = 16.dp, start = 16.dp, end = 16.dp)
                ) {
                    Text(
                        warning,
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
                    .background(Color.Black.copy(alpha = 0.65f))
                    .padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                if (isCapturing) {
                    CircularProgressIndicator(color = Color.White)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("Capturing high-resolution photo...", color = Color.White, fontSize = 12.sp)
                } else {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceEvenly,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        // Gallery button
                        IconButton(
                            onClick = {
                                photoPickerLauncher.launch(
                                    PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                                )
                            },
                            modifier = Modifier
                                .size(48.dp)
                                .background(Color.White.copy(alpha = 0.2f), CircleShape)
                        ) {
                            Icon(Icons.Default.PhotoLibrary, contentDescription = "Gallery", tint = Color.White)
                        }

                        // Capture Shutter Button
                        IconButton(
                            onClick = {
                                val capture = imageCapture
                                if (capture == null) {
                                    qualityWarning = "Camera not ready. Please select from gallery."
                                    return@IconButton
                                }
                                isCapturing = true
                                qualityWarning = null

                                val photoFile = File(cacheDir, "specimen_${UUID.randomUUID()}.jpg")
                                val outputOptions = ImageCapture.OutputFileOptions.Builder(photoFile).build()

                                capture.takePicture(
                                    outputOptions,
                                    ContextCompat.getMainExecutor(context),
                                    object : ImageCapture.OnImageSavedCallback {
                                        override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                                            isCapturing = false
                                            // Validate quality check
                                            try {
                                                val bmp = BitmapFactory.decodeFile(photoFile.absolutePath)
                                                if (bmp != null) {
                                                    val quality = ImageQualityValidator.evaluate(bmp)
                                                    if (quality.warningMessage != null) {
                                                        qualityWarning = quality.warningMessage
                                                    }
                                                }
                                            } catch (_: Exception) {}

                                            onPhotoSelected(photoFile.absolutePath)
                                        }

                                        override fun onError(exc: ImageCaptureException) {
                                            isCapturing = false
                                            qualityWarning = "Capture failed: ${exc.message}"
                                        }
                                    }
                                )
                            },
                            modifier = Modifier
                                .size(72.dp)
                                .background(Color.White, CircleShape)
                        ) {
                            Icon(
                                Icons.Default.CameraAlt,
                                contentDescription = "Capture Photograph",
                                tint = Color.Black,
                                modifier = Modifier.size(36.dp)
                            )
                        }

                        // Flash Indicator status
                        IconButton(
                            onClick = {
                                flashMode = when (flashMode) {
                                    ImageCapture.FLASH_MODE_OFF -> ImageCapture.FLASH_MODE_ON
                                    else -> ImageCapture.FLASH_MODE_OFF
                                }
                                imageCapture?.flashMode = flashMode
                            },
                            modifier = Modifier
                                .size(48.dp)
                                .background(Color.White.copy(alpha = 0.2f), CircleShape)
                        ) {
                            Icon(
                                if (flashMode == ImageCapture.FLASH_MODE_ON) Icons.Default.FlashOn else Icons.Default.FlashOff,
                                contentDescription = "Flash",
                                tint = Color.White
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))
                    Text(
                        "Tap to capture high-res photograph • Gallery also supported",
                        color = Color.White.copy(alpha = 0.75f),
                        fontSize = 11.sp
                    )
                }
            }
        }
    }
}
