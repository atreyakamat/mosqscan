package com.vectora.ai.ui.screens

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vectora.ai.data.local.db.SubmissionDao
import com.vectora.ai.data.local.db.SubmissionEntity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.util.UUID

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AdultCropScreen(
    imagePath: String,
    submissionDao: SubmissionDao,
    cacheDir: File,
    onRetake: () -> Unit,
    onConfirmCrop: (submissionId: String) -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    var currentPath by remember { mutableStateOf(imagePath) }
    var bitmap by remember { mutableStateOf<Bitmap?>(null) }
    var rotationDegrees by remember { mutableFloatStateOf(0f) }

    // Normalized crop rectangle [0, 1]
    var cropSize by remember { mutableFloatStateOf(0.70f) }
    var cropX by remember { mutableFloatStateOf(0.15f) }
    var cropY by remember { mutableFloatStateOf(0.15f) }

    var isSaving by remember { mutableStateOf(false) }

    // Android Photo Picker for picking another image from gallery
    val photoPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia()
    ) { uri: Uri? ->
        if (uri != null) {
            coroutineScope.launch {
                val newFile = File(cacheDir, "gallery_${UUID.randomUUID()}.jpg")
                withContext(Dispatchers.IO) {
                    context.contentResolver.openInputStream(uri)?.use { input ->
                        FileOutputStream(newFile).use { output ->
                            input.copyTo(output)
                        }
                    }
                }
                currentPath = newFile.absolutePath
                rotationDegrees = 0f
            }
        }
    }

    // Load bitmap and apply EXIF orientation plus manual rotation
    LaunchedEffect(currentPath, rotationDegrees) {
        withContext(Dispatchers.IO) {
            try {
                val orig = BitmapFactory.decodeFile(currentPath)
                if (orig != null) {
                    var exifRotation = 0f
                    try {
                        val exif = ExifInterface(currentPath)
                        val orientation = exif.getAttributeInt(
                            ExifInterface.TAG_ORIENTATION,
                            ExifInterface.ORIENTATION_NORMAL
                        )
                        exifRotation = when (orientation) {
                            ExifInterface.ORIENTATION_ROTATE_90 -> 90f
                            ExifInterface.ORIENTATION_ROTATE_180 -> 180f
                            ExifInterface.ORIENTATION_ROTATE_270 -> 270f
                            else -> 0f
                        }
                    } catch (_: Exception) {}

                    val totalRotation = (exifRotation + rotationDegrees) % 360f
                    if (totalRotation != 0f) {
                        val matrix = Matrix().apply { postRotate(totalRotation) }
                        bitmap = Bitmap.createBitmap(orig, 0, 0, orig.width, orig.height, matrix, true)
                    } else {
                        bitmap = orig
                    }
                } else {
                    bitmap = null
                }
            } catch (_: Exception) {
                bitmap = null
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Specimen Preview & Crop", fontSize = 18.sp, fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onRetake) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Retake")
                    }
                },
                actions = {
                    // 90 degree clockwise rotation button
                    IconButton(onClick = {
                        rotationDegrees = (rotationDegrees + 90f) % 360f
                    }) {
                        Icon(Icons.Default.RotateRight, contentDescription = "Rotate 90 degrees")
                    }
                    // Choose another from Gallery
                    IconButton(onClick = {
                        photoPickerLauncher.launch(
                            PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                        )
                    }) {
                        Icon(Icons.Default.PhotoLibrary, contentDescription = "Choose from Gallery")
                    }
                }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(MaterialTheme.colorScheme.background)
        ) {
            // Main image preview with interactive framing overlay
            BoxWithConstraints(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .background(Color.Black),
                contentAlignment = Alignment.Center
            ) {
                val containerW = maxWidth
                val containerH = maxHeight

                if (bitmap != null) {
                    Image(
                        bitmap = bitmap!!.asImageBitmap(),
                        contentDescription = "Specimen Preview",
                        contentScale = ContentScale.Fit,
                        modifier = Modifier.fillMaxSize()
                    )

                    // Square crop box matching model input dimensions
                    val sideDim = minOf(containerW, containerH) * cropSize
                    val boxW = sideDim
                    val boxH = sideDim
                    val maxOffsetX = (containerW - boxW).coerceAtLeast(0.dp)
                    val maxOffsetY = (containerH - boxH).coerceAtLeast(0.dp)
                    val offsetX = maxOffsetX * if (1f - cropSize > 0.001f) (cropX / (1f - cropSize)).coerceIn(0f, 1f) else 0f
                    val offsetY = maxOffsetY * if (1f - cropSize > 0.001f) (cropY / (1f - cropSize)).coerceIn(0f, 1f) else 0f

                    Box(
                        modifier = Modifier
                            .offset(x = offsetX, y = offsetY)
                            .size(width = boxW, height = boxH)
                            .border(2.dp, Color(0xFFFFD54F), MaterialTheme.shapes.small)
                            .background(Color(0xFFFFD54F).copy(alpha = 0.15f))
                            .pointerInput(cropSize, containerW, containerH) {
                                detectDragGestures { change, dragAmount ->
                                    change.consume()
                                    val deltaXNorm = dragAmount.x / containerW.toPx()
                                    val deltaYNorm = dragAmount.y / containerH.toPx()
                                    cropX = (cropX + deltaXNorm).coerceIn(0f, 1f - cropSize)
                                    cropY = (cropY + deltaYNorm).coerceIn(0f, 1f - cropSize)
                                }
                            }
                    ) {
                        Text(
                            "Specimen Crop Area (Drag to reposition)",
                            color = Color(0xFFFFD54F),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier
                                .align(Alignment.TopCenter)
                                .background(Color.Black.copy(alpha = 0.7f))
                                .padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                } else {
                    CircularProgressIndicator(color = Color.White)
                }
            }

            // Crop Adjustment Sliders & Specimen Framing Information
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(12.dp)
            ) {
                Column(
                    modifier = Modifier.padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            "Specimen Crop Framing",
                            fontWeight = FontWeight.Bold,
                            fontSize = 13.sp
                        )
                        OutlinedButton(
                            onClick = {
                                cropSize = 0.70f
                                cropX = 0.15f
                                cropY = 0.15f
                            },
                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                            modifier = Modifier.height(28.dp)
                        ) {
                            Text("Center Crop", fontSize = 11.sp)
                        }
                    }

                    Text(
                        "Drag the yellow box or adjust sliders to isolate the mosquito specimen. The i7 classifier requires manual framing for highest accuracy.",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    // Crop Size (Zoom) Slider
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Window Size:", fontSize = 12.sp)
                        Slider(
                            value = cropSize,
                            onValueChange = { newSize ->
                                cropSize = newSize
                                if (cropX + newSize > 1f) cropX = 1f - newSize
                                if (cropY + newSize > 1f) cropY = 1f - newSize
                            },
                            valueRange = 0.25f..0.95f,
                            modifier = Modifier.weight(1f).padding(horizontal = 8.dp)
                        )
                        Text(String.format("%.0f%%", cropSize * 100), fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    }

                    // Position X Slider
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Horizontal X:", fontSize = 12.sp)
                        Slider(
                            value = cropX,
                            onValueChange = { cropX = it.coerceIn(0f, 1f - cropSize) },
                            valueRange = 0f..((1f - cropSize).coerceAtLeast(0.01f)),
                            modifier = Modifier.weight(1f).padding(horizontal = 8.dp)
                        )
                        Text(String.format("%.0f%%", cropX * 100), fontSize = 12.sp)
                    }

                    // Position Y Slider
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Vertical Y:", fontSize = 12.sp)
                        Slider(
                            value = cropY,
                            onValueChange = { cropY = it.coerceIn(0f, 1f - cropSize) },
                            valueRange = 0f..((1f - cropSize).coerceAtLeast(0.01f)),
                            modifier = Modifier.weight(1f).padding(horizontal = 8.dp)
                        )
                        Text(String.format("%.0f%%", cropY * 100), fontSize = 12.sp)
                    }
                }
            }

            // Bottom action buttons: Retake and Confirm & Upload
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                OutlinedButton(
                    onClick = onRetake,
                    modifier = Modifier.weight(1f)
                ) {
                    Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Retake")
                }

                Button(
                    onClick = {
                        isSaving = true
                        coroutineScope.launch {
                            val subId = UUID.randomUUID().toString()

                            // Save properly oriented bitmap to file so coordinates match orientation on server
                            val finalImagePath = if (bitmap != null) {
                                val orientedFile = File(cacheDir, "specimen_oriented_$subId.jpg")
                                withContext(Dispatchers.IO) {
                                    FileOutputStream(orientedFile).use { out ->
                                        bitmap!!.compress(Bitmap.CompressFormat.JPEG, 95, out)
                                    }
                                }
                                orientedFile.absolutePath
                            } else {
                                currentPath
                            }

                            // Create Room SubmissionEntity with status = PENDING_UPLOAD
                            val entity = SubmissionEntity(
                                id = subId,
                                type = "adult",
                                imagePath = finalImagePath,
                                videoPath = null,
                                predictedGenus = null,
                                confidence = null,
                                isUncertain = true,
                                modelVersion = "3.0.0",
                                processingTimeMs = null,
                                createdAt = System.currentTimeMillis(),
                                synced = false,
                                status = "PENDING_UPLOAD",
                                rawScore = null,
                                modelStatus = "EXPERIMENTAL_NOT_FIELD_VALIDATED",
                                cropX = cropX,
                                cropY = cropY,
                                cropW = cropSize,
                                cropH = cropSize
                            )

                            withContext(Dispatchers.IO) {
                                submissionDao.insert(entity)
                            }

                            isSaving = false
                            onConfirmCrop(subId)
                        }
                    },
                    enabled = !isSaving && bitmap != null,
                    modifier = Modifier.weight(1f)
                ) {
                    if (isSaving) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.White)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Preparing...")
                    } else {
                        Icon(Icons.Default.CloudUpload, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Confirm & Upload")
                    }
                }
            }
        }
    }
}
