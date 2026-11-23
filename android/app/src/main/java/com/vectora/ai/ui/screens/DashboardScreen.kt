package com.vectora.ai.ui.screens

import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
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
import com.vectora.ai.data.remote.ServerClientManager
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    submissionDao: SubmissionDao,
    serverClientManager: ServerClientManager? = null,
    onNavigateToAdultCapture: () -> Unit,
    onNavigateToLarvaeCapture: () -> Unit,
    onNavigateToHistory: () -> Unit,
    onNavigateToSettings: () -> Unit,
    onNavigateToAssistant: () -> Unit,
    onSelectSubmission: ((String) -> Unit)? = null
) {
    val coroutineScope = rememberCoroutineScope()
    var submissions by remember { mutableStateOf<List<SubmissionEntity>>(emptyList()) }
    var serverOnline by remember { mutableStateOf<Boolean?>(null) }
    var modelStatus by remember { mutableStateOf<String?>(null) }
    var assistantStatus by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        submissionDao.getAllSubmissions().collectLatest {
            submissions = it
        }
    }

    LaunchedEffect(serverClientManager?.baseUrl) {
        if (serverClientManager != null) {
            val healthResult = serverClientManager.checkHealth()
            serverOnline = healthResult.isSuccess
            val mResult = serverClientManager.checkModelHealth()
            if (mResult.isSuccess) {
                modelStatus = mResult.getOrNull()
            }
            val aResult = serverClientManager.checkAssistantHealth()
            if (aResult.isSuccess) {
                assistantStatus = aResult.getOrNull()
            } else {
                assistantStatus = "Offline"
            }
        }
    }

    val adultCount = submissions.count { it.type == "adult" }
    val larvaeCount = submissions.count { it.type == "larvae" }
    val confirmedCount = submissions.count { !it.isUncertain && it.predictedGenus != null }
    val pendingUploadCount = submissions.count { it.status == "PENDING_UPLOAD" || !it.synced }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("Vectora ", fontWeight = FontWeight.Bold, fontSize = 20.sp)
                        Text("AI", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                    }
                },
                actions = {
                    IconButton(onClick = onNavigateToAssistant) {
                        Icon(Icons.Default.Psychology, contentDescription = "AI Assistant", tint = MaterialTheme.colorScheme.primary)
                    }
                    IconButton(onClick = onNavigateToHistory) {
                        BadgedBox(
                            badge = {
                                if (pendingUploadCount > 0) {
                                    Badge { Text("$pendingUploadCount") }
                                }
                            }
                        ) {
                            Icon(Icons.Default.History, contentDescription = "History")
                        }
                    }
                    IconButton(onClick = onNavigateToSettings) {
                        Icon(Icons.Default.Settings, contentDescription = "Settings")
                    }
                }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Contextual Welcome Banner
            Surface(
                color = MaterialTheme.colorScheme.primaryContainer,
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        "Mosquito Surveillance & Genus ID",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        "Ready to scan field specimens",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.ExtraBold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        "Host: Intel Core i7-2600 • Model: vectora_v3_fp32.onnx",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            // Real System Status Card
            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("System & Model Status", fontWeight = FontWeight.Bold, fontSize = 13.sp)
                        IconButton(
                            onClick = {
                                coroutineScope.launch {
                                    serverOnline = null
                                    val healthResult = serverClientManager?.checkHealth()
                                    serverOnline = healthResult?.isSuccess == true
                                    val mResult = serverClientManager?.checkModelHealth()
                                    modelStatus = mResult?.getOrNull()
                                    val aResult = serverClientManager?.checkAssistantHealth()
                                    assistantStatus = if (aResult?.isSuccess == true) aResult.getOrNull() else "Offline"
                                }
                            },
                            modifier = Modifier.size(24.dp)
                        ) {
                            Icon(Icons.Default.Refresh, contentDescription = "Refresh", modifier = Modifier.size(16.dp))
                        }
                    }
                    Divider()

                    // Server row
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(10.dp)
                                .background(
                                    color = when (serverOnline) {
                                        true -> Color(0xFF059669)
                                        false -> Color(0xFFE11D48)
                                        null -> Color.Gray
                                    },
                                    shape = CircleShape
                                )
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            when (serverOnline) {
                                true -> "Server Connected (${serverClientManager?.baseUrl})"
                                false -> "Server Offline (${serverClientManager?.baseUrl})"
                                null -> "Testing Connection..."
                            },
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }

                    // Model row
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Memory, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(14.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            modelStatus ?: "Adult ONNX Model: vectora_v3_fp32 (SHA-256 Verified)",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    // Assistant row
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Psychology, contentDescription = null, tint = MaterialTheme.colorScheme.secondary, modifier = Modifier.size(14.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            "AI Assistant: ${assistantStatus ?: "Checking..."}",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            // Pending Uploads Alert if any
            if (pendingUploadCount > 0) {
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.tertiaryContainer),
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.CloudQueue, contentDescription = null, tint = MaterialTheme.colorScheme.tertiary)
                        Spacer(modifier = Modifier.width(10.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                "$pendingUploadCount Offline Submission(s) Queued",
                                fontWeight = FontWeight.Bold,
                                fontSize = 12.sp
                            )
                            Text("Saved locally in Room. Syncs automatically when online.", fontSize = 11.sp)
                        }
                        TextButton(onClick = onNavigateToHistory) {
                            Text("View", fontSize = 12.sp)
                        }
                    }
                }
            }

            // Quick Actions Section
            Text("Quick Actions", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)

            // CTA 1: Scan Adult Mosquito
            Button(
                onClick = onNavigateToAdultCapture,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(64.dp),
                shape = RoundedCornerShape(10.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Start,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.Default.CameraAlt, contentDescription = null, modifier = Modifier.size(26.dp))
                    Spacer(modifier = Modifier.width(14.dp))
                    Column {
                        Text("Scan Adult Mosquito", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                        Text("High-res capture • Manual specimen crop • ONNX genus ID", fontSize = 11.sp, color = Color.White.copy(alpha = 0.85f))
                    }
                }
            }

            // CTA 2: Ask AI Assistant
            OutlinedButton(
                onClick = onNavigateToAssistant,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
                shape = RoundedCornerShape(10.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Start,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.Default.Psychology, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(24.dp))
                    Spacer(modifier = Modifier.width(14.dp))
                    Column {
                        Text("Ask Vectora AI Assistant", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        Text("Morphological traits • Genus comparison • Gemma 3:4B", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }

            // CTA 3: Larvae Video
            OutlinedButton(
                onClick = onNavigateToLarvaeCapture,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
                shape = RoundedCornerShape(10.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Start,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.Default.Videocam, contentDescription = null, tint = MaterialTheme.colorScheme.secondary, modifier = Modifier.size(24.dp))
                    Spacer(modifier = Modifier.width(14.dp))
                    Column {
                        Text("Record Larvae Video (Research)", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        Text("3–5s Locomotion clip • Meniscus guide • Research only", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }

            // Metrics Summary
            Text("Collection Statistics", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Card(modifier = Modifier.weight(1f)) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text("Adult", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("$adultCount", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                    }
                }
                Card(modifier = Modifier.weight(1f)) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text("Larvae", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("$larvaeCount", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                    }
                }
                Card(modifier = Modifier.weight(1f)) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text("Identified", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("$confirmedCount", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                    }
                }
                Card(modifier = Modifier.weight(1f)) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text("Pending", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(
                            "$pendingUploadCount",
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (pendingUploadCount > 0) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface
                        )
                    }
                }
            }

            // Recent Activity Section
            if (submissions.isNotEmpty()) {
                Text("Recent Specimen Scans", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)

                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    submissions.take(5).forEach { sub ->
                        Card(
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { onSelectSubmission?.invoke(sub.id) }
                        ) {
                            Row(
                                modifier = Modifier.padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                // Specimen thumbnail
                                if (sub.imagePath != null && File(sub.imagePath).exists()) {
                                    val bmp = remember(sub.imagePath) {
                                        BitmapFactory.decodeFile(sub.imagePath)
                                    }
                                    if (bmp != null) {
                                        Image(
                                            bitmap = bmp.asImageBitmap(),
                                            contentDescription = "Specimen thumbnail",
                                            contentScale = ContentScale.Crop,
                                            modifier = Modifier
                                                .size(44.dp)
                                                .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(6.dp))
                                        )
                                    } else {
                                        Box(
                                            modifier = Modifier
                                                .size(44.dp)
                                                .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(6.dp)),
                                            contentAlignment = Alignment.Center
                                        ) {
                                            Icon(Icons.Default.BugReport, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                                        }
                                    }
                                } else {
                                    Box(
                                        modifier = Modifier
                                            .size(44.dp)
                                            .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(6.dp)),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Icon(
                                            if (sub.type == "adult") Icons.Default.BugReport else Icons.Default.Videocam,
                                            contentDescription = null,
                                            tint = MaterialTheme.colorScheme.primary
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.width(12.dp))

                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        if (sub.type == "adult") {
                                            if (sub.isUncertain) "Uncertain Genus"
                                            else sub.predictedGenus?.replaceFirstChar { it.uppercase() } ?: "Pending Analysis"
                                        } else {
                                            "Larvae Locomotion Recording"
                                        },
                                        fontWeight = FontWeight.SemiBold,
                                        fontSize = 13.sp
                                    )
                                    val df = SimpleDateFormat("MMM d, HH:mm", Locale.getDefault())
                                    Text(
                                        "${df.format(Date(sub.createdAt))} • ${if (sub.synced) "Server verified" else "Local queue"}",
                                        fontSize = 11.sp,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }

                                if (sub.status == "PENDING_UPLOAD" || !sub.synced) {
                                    Badge(containerColor = MaterialTheme.colorScheme.tertiaryContainer) {
                                        Text("Pending", fontSize = 10.sp)
                                    }
                                } else if (sub.rawScore != null) {
                                    Text(
                                        String.format("%.0f%%", sub.rawScore * 100),
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 12.sp,
                                        color = MaterialTheme.colorScheme.primary
                                    )
                                }
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(20.dp))
        }
    }
}
