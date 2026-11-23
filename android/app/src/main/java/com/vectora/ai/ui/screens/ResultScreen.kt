package com.vectora.ai.ui.screens

import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vectora.ai.data.local.db.SubmissionDao
import com.vectora.ai.data.local.db.SubmissionEntity
import com.vectora.ai.data.remote.ServerClientManager
import com.vectora.ai.ui.theme.*
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
    serverClientManager: ServerClientManager? = null,
    onBackToDashboard: () -> Unit,
    onNavigateToHistory: (() -> Unit)? = null,
    onRetryUpload: ((submissionId: String) -> Unit)? = null
) {
    var submission by remember { mutableStateOf<SubmissionEntity?>(null) }
    var loading by remember { mutableStateOf(true) }

    LaunchedEffect(submissionId) {
        val sub = withContext(Dispatchers.IO) {
            submissionDao.getSubmissionById(submissionId)
        }
        submission = sub
        loading = false
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Scan Result", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = VectoraSlate900) },
                navigationIcon = {
                    IconButton(onClick = onBackToDashboard) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back", tint = VectoraSlate700)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background
                )
            )
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { paddingValues ->
        if (loading) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator(color = VectoraTeal)
            }
        } else if (submission == null) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues),
                contentAlignment = Alignment.Center
            ) {
                Text("Submission record not found", color = VectoraSlate700)
            }
        } else {
            val sub = submission!!
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues)
                    .padding(horizontal = 20.dp, vertical = 12.dp)
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // 1. Specimen Photograph
                sub.imagePath?.let { path ->
                    val file = File(path)
                    if (file.exists()) {
                        val bitmap = remember(path) { BitmapFactory.decodeFile(path) }
                        if (bitmap != null) {
                            Card(
                                shape = RoundedCornerShape(12.dp),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(220.dp)
                                    .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(12.dp)),
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                            ) {
                                Image(
                                    bitmap = bitmap.asImageBitmap(),
                                    contentDescription = "Specimen Photograph",
                                    contentScale = ContentScale.Fit,
                                    modifier = Modifier
                                        .fillMaxSize()
                                        .clip(RoundedCornerShape(12.dp))
                                )
                            }
                        }
                    }
                }

                // 2. Pending Upload Status (if offline)
                if (sub.status == "PENDING_UPLOAD" || !sub.synced) {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = VectoraAmberContainer),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier.padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = Icons.Default.CloudQueue,
                                contentDescription = null,
                                tint = VectoraAmber,
                                modifier = Modifier.size(28.dp)
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Column {
                                Text(
                                    text = "Status: PENDING_UPLOAD",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 14.sp,
                                    color = VectoraAmber
                                )
                                Spacer(modifier = Modifier.height(2.dp))
                                Text(
                                    text = "Specimen saved locally in Room queue. Inference will execute when server connection is restored.",
                                    fontSize = 12.sp,
                                    color = VectoraSlate700,
                                    lineHeight = 16.sp
                                )
                            }
                        }
                    }
                } else if (sub.type == "adult") {
                    // 3. Predicted Genus Card
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(12.dp)),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = if (sub.isUncertain || sub.predictedGenus == null) {
                                VectoraAmberContainer
                            } else {
                                VectoraTealContainer
                            }
                        )
                    ) {
                        Column(modifier = Modifier.padding(18.dp)) {
                            Text(
                                text = "PREDICTED GENUS",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (sub.isUncertain || sub.predictedGenus == null) VectoraAmber else VectoraTeal
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = if (sub.isUncertain || sub.predictedGenus == null) {
                                    "Uncertain Genus"
                                } else {
                                    sub.predictedGenus?.replaceFirstChar { it.uppercase() } ?: "Unknown"
                                },
                                fontSize = 28.sp,
                                fontWeight = FontWeight.ExtraBold,
                                color = VectoraSlate900
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            if (sub.isUncertain || sub.predictedGenus == null) {
                                Text(
                                    text = "Highest raw activation is below certainty threshold (65%). Prediction not forced.",
                                    fontSize = 12.sp,
                                    color = VectoraSlate700
                                )
                            }
                        }
                    }

                    // 4. Three Raw Model Scores
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(12.dp)),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                    ) {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            Text(
                                text = "Three Raw Model Scores",
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp,
                                color = VectoraSlate900
                            )
                            Text(
                                text = "Uncalibrated softmax activations across target classes. Not field-calibrated probabilities.",
                                fontSize = 11.sp,
                                color = VectoraSlate500
                            )

                            val hasAllScores = sub.scoreAedes != null && sub.scoreAnopheles != null && sub.scoreCulex != null

                            if (hasAllScores) {
                                ScoreRow(name = "Aedes", score = sub.scoreAedes, barColor = VectoraTeal)
                                ScoreRow(name = "Anopheles", score = sub.scoreAnopheles, barColor = VectoraTealDark)
                                ScoreRow(name = "Culex", score = sub.scoreCulex, barColor = VectoraSlate500)
                            } else if (sub.rawScore != null && sub.predictedGenus != null) {
                                ScoreRow(
                                    name = sub.predictedGenus.replaceFirstChar { it.uppercase() },
                                    score = sub.rawScore,
                                    barColor = VectoraTeal
                                )
                            } else {
                                Text(
                                    text = "Detailed class scores not available for this record.",
                                    fontSize = 12.sp,
                                    color = VectoraSlate500
                                )
                            }
                        }
                    }
                } else {
                    // Larvae Specimen Notice
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(12.dp)),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = VectoraAmberContainer)
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.Info, contentDescription = null, tint = VectoraAmber)
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    "Larvae Research Specimen",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 14.sp,
                                    color = VectoraAmber
                                )
                            }
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                "Model is not field-validated. Locomotion clip recorded within 3–5 second limit and preserved strictly for research.",
                                fontSize = 12.sp,
                                color = VectoraSlate700
                            )
                        }
                    }
                }

                // 5. Scan Time & Model Version Metadata
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(12.dp)),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text(
                            "Inference Metadata",
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp,
                            color = VectoraSlate900
                        )
                        HorizontalDivider(color = VectoraSlate200)

                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Model Version", fontSize = 12.sp, color = VectoraSlate500)
                            Text(sub.modelVersion, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = VectoraSlate900)
                        }

                        if (sub.processingTimeMs != null) {
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text("Inference Duration", fontSize = 12.sp, color = VectoraSlate500)
                                Text("${sub.processingTimeMs} ms", fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = VectoraSlate900)
                            }
                        }

                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Scan Time", fontSize = 12.sp, color = VectoraSlate500)
                            val df = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
                            Text(df.format(Date(sub.createdAt)), fontSize = 12.sp, color = VectoraSlate900)
                        }
                    }
                }

                // 6. Manual Review Notice (EXPERIMENTAL_NOT_FIELD_VALIDATED)
                Card(
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = VectoraSlate100),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(14.dp),
                        verticalAlignment = Alignment.Top
                    ) {
                        Icon(
                            Icons.Default.Info,
                            contentDescription = null,
                            tint = VectoraSlate700,
                            modifier = Modifier.size(20.dp).padding(top = 1.dp)
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Column {
                            Text(
                                "EXPERIMENTAL_NOT_FIELD_VALIDATED",
                                fontWeight = FontWeight.Bold,
                                fontSize = 11.sp,
                                color = VectoraSlate900
                            )
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                "Output is an uncalibrated experimental heuristic. Confirmatory entomological inspection advised. Pathogen detection not supported.",
                                fontSize = 11.sp,
                                color = VectoraSlate700,
                                lineHeight = 15.sp
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(4.dp))

                // Action Buttons
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    if (sub.status == "PENDING_UPLOAD" && onRetryUpload != null) {
                        Button(
                            onClick = { onRetryUpload(sub.id) },
                            modifier = Modifier.weight(1f).height(48.dp),
                            shape = RoundedCornerShape(10.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = VectoraTeal)
                        ) {
                            Icon(Icons.Default.Upload, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Retry Upload")
                        }
                    }

                    Button(
                        onClick = onBackToDashboard,
                        modifier = Modifier.weight(1f).height(48.dp),
                        shape = RoundedCornerShape(10.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = VectoraTeal)
                    ) {
                        Text("Done", fontWeight = FontWeight.SemiBold)
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))
            }
        }
    }
}

@Composable
private fun ScoreRow(
    name: String,
    score: Float?,
    barColor: Color
) {
    val s = score ?: 0f
    Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(name, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = VectoraSlate900)
            Text(
                text = if (score != null) String.format("%.4f", s) else "N/A",
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium,
                color = VectoraSlate700
            )
        }
        LinearProgressIndicator(
            progress = { s.coerceIn(0f, 1f) },
            modifier = Modifier
                .fillMaxWidth()
                .height(6.dp)
                .clip(RoundedCornerShape(3.dp)),
            color = barColor,
            trackColor = VectoraSlate200
        )
    }
}
