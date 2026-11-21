package com.vectora.ai.ui.screens

import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
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
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vectora.ai.data.local.db.SubmissionDao
import com.vectora.ai.data.local.db.SubmissionEntity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ResultScreen(
    submissionId: String,
    submissionDao: SubmissionDao,
    onBackToDashboard: () -> Unit,
    onNavigateToHistory: () -> Unit,
    onRetryUpload: ((submissionId: String) -> Unit)? = null
) {
    var submission by remember { mutableStateOf<SubmissionEntity?>(null) }
    var loading by remember { mutableStateOf(true) }

    LaunchedEffect(submissionId) {
        submission = withContext(Dispatchers.IO) {
            submissionDao.getSubmissionById(submissionId)
        }
        loading = false
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Identification Result", fontSize = 18.sp, fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBackToDashboard) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Dashboard")
                    }
                }
            )
        }
    ) { paddingValues ->
        if (loading) {
            Box(modifier = Modifier.fillMaxSize().padding(paddingValues), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        } else if (submission == null) {
            Box(modifier = Modifier.fillMaxSize().padding(paddingValues), contentAlignment = Alignment.Center) {
                Text("Submission not found")
            }
        } else {
            val sub = submission!!
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues)
                    .padding(16.dp)
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Specimen Image Preview if available
                sub.imagePath?.let { path ->
                    val file = File(path)
                    if (file.exists()) {
                        val bitmap = remember(path) { BitmapFactory.decodeFile(path) }
                        if (bitmap != null) {
                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(200.dp)
                            ) {
                                Image(
                                    bitmap = bitmap.asImageBitmap(),
                                    contentDescription = "Uploaded Specimen",
                                    contentScale = ContentScale.Crop,
                                    modifier = Modifier.fillMaxSize()
                                )
                            }
                        }
                    }
                }

                // Check pending state
                if (sub.status == "PENDING_UPLOAD" || !sub.synced) {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.tertiaryContainer),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.CloudQueue, contentDescription = null, tint = MaterialTheme.colorScheme.tertiary)
                            Spacer(modifier = Modifier.width(12.dp))
                            Column {
                                Text("Pending Upload to Server", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                                Text(
                                    "This specimen was captured offline or server was unavailable. Model prediction will be obtained once uploaded to the i7 server.",
                                    fontSize = 12.sp
                                )
                            }
                        }
                    }
                } else if (sub.type == "adult") {
                    // Result Card for Adult
                    if (sub.isUncertain || sub.predictedGenus == null) {
                        Card(
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.Warning, contentDescription = null, tint = MaterialTheme.colorScheme.error)
                                Spacer(modifier = Modifier.width(12.dp))
                                Column {
                                    val msg = if ((sub.rawScore ?: sub.confidence ?: 0f) < 0.40f) {
                                        "Non-target object detected."
                                    } else {
                                        "Uncertain identification. Manual inspection is advised."
                                    }
                                    Text(msg, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(
                                        String.format(
                                            "Raw model score (%.1f%%) is below the 65%% certainty threshold. The system will not force a classification.",
                                            (sub.rawScore ?: sub.confidence ?: 0f) * 100
                                        ),
                                        fontSize = 12.sp
                                    )
                                }
                            }
                        }
                    } else {
                        // Confident Genus identification
                        Card(
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Text(
                                    "IDENTIFIED GENUS",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.primary
                                )
                                Text(
                                    sub.predictedGenus?.replaceFirstChar { it.uppercase() } ?: "Unknown",
                                    fontSize = 28.sp,
                                    fontWeight = FontWeight.ExtraBold,
                                    color = MaterialTheme.colorScheme.onPrimaryContainer
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    String.format("Raw Model Score: %.1f%%", (sub.rawScore ?: sub.confidence ?: 0f) * 100),
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.SemiBold
                                )
                            }
                        }
                    }

                    // Model Safety & Scientific Disclaimer Banner
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(modifier = Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Info, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Column {
                                Text(
                                    "EXPERIMENTAL_NOT_FIELD_VALIDATED",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 11.sp,
                                    color = MaterialTheme.colorScheme.primary
                                )
                                Text(
                                    "Raw softmax output is an uncalibrated experimental heuristic. Visual identification only. Not field-validated for epidemiological decisions.",
                                    fontSize = 10.sp,
                                    lineHeight = 13.sp
                                )
                            }
                        }
                    }
                } else {
                    // Larvae Result
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.tertiaryContainer),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.Info, contentDescription = null, tint = MaterialTheme.colorScheme.tertiary)
                                Spacer(modifier = Modifier.width(8.dp))
                                Text("Larvae Model: Not Field-Validated", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                            }
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                "Larvae identification model is not field-validated. Locomotion clip duration strictly validated (3–5 seconds) and preserved for research.",
                                fontSize = 12.sp
                            )
                        }
                    }
                }

                // Metadata Card
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Inference & Specimen Metadata", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        Divider()

                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Specimen Type", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text(sub.type.replaceFirstChar { it.uppercase() }, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                        }

                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Model Version", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text(sub.modelVersion, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                        }

                        if (sub.processingTimeMs != null) {
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text("Server Processing Duration", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text("${sub.processingTimeMs} ms", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                            }
                        }

                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("AI Inference Host", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("Intel Core i7-2600 CPU (Exp B FP32)", fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                        }

                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Captured At", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            val df = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
                            Text(df.format(Date(sub.createdAt)), fontSize = 12.sp)
                        }

                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Sync Status", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text(
                                if (sub.synced) "Completed on Server" else "Pending Upload (Offline)",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = if (sub.synced) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
                            )
                        }
                    }
                }

                // Action Buttons
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    if (sub.status == "PENDING_UPLOAD" && onRetryUpload != null) {
                        Button(
                            onClick = { onRetryUpload(sub.id) },
                            modifier = Modifier.weight(1f)
                        ) {
                            Icon(Icons.Default.Upload, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Upload Now")
                        }
                    } else {
                        OutlinedButton(
                            onClick = onNavigateToHistory,
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("History")
                        }
                        Button(
                            onClick = onBackToDashboard,
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Done")
                        }
                    }
                }
            }
        }
    }
}
