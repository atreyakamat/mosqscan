package com.vectora.ai.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
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
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    submissionDao: SubmissionDao,
    serverClientManager: ServerClientManager? = null,
    onNavigateToAdultCapture: () -> Unit,
    onNavigateToLarvaeCapture: () -> Unit,
    onNavigateToHistory: () -> Unit,
    onNavigateToSettings: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    var submissions by remember { mutableStateOf<List<SubmissionEntity>>(emptyList()) }
    var serverOnline by remember { mutableStateOf<Boolean?>(null) }
    var serverVersion by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        submissionDao.getAllSubmissions().collectLatest {
            submissions = it
        }
    }

    LaunchedEffect(serverClientManager?.baseUrl) {
        if (serverClientManager != null) {
            val result = serverClientManager.checkHealth()
            if (result.isSuccess) {
                serverOnline = true
                serverVersion = result.getOrNull()
            } else {
                serverOnline = false
                serverVersion = null
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
                        Text("Vectora ", fontWeight = FontWeight.Bold)
                        Text("AI", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                    }
                },
                actions = {
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
            // Live Server Status Indicator Banner
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = when (serverOnline) {
                        true -> MaterialTheme.colorScheme.primaryContainer
                        false -> MaterialTheme.colorScheme.errorContainer
                        null -> MaterialTheme.colorScheme.surfaceVariant
                    }
                ),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier.padding(14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(12.dp)
                            .background(
                                color = when (serverOnline) {
                                    true -> Color(0xFF2E7D32)
                                    false -> Color(0xFFC62828)
                                    null -> Color.Gray
                                },
                                shape = CircleShape
                            )
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            when (serverOnline) {
                                true -> "Inference Server Online"
                                false -> "Inference Server Offline"
                                null -> "Checking Server Status..."
                            },
                            fontWeight = FontWeight.Bold,
                            fontSize = 13.sp
                        )
                        Text(
                            when (serverOnline) {
                                true -> "${serverClientManager?.baseUrl} • Intel Core i7-2600"
                                false -> "Captures queue locally until connectivity is restored"
                                null -> "Connecting..."
                            },
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    IconButton(
                        onClick = {
                            coroutineScope.launch {
                                serverOnline = null
                                val result = serverClientManager?.checkHealth()
                                serverOnline = result?.isSuccess == true
                            }
                        },
                        modifier = Modifier.size(28.dp)
                    ) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh", modifier = Modifier.size(16.dp))
                    }
                }
            }

            // Pending Uploads Alert if any
            if (pendingUploadCount > 0) {
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.tertiaryContainer),
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
                                "$pendingUploadCount Offline Submission(s) Pending",
                                fontWeight = FontWeight.Bold,
                                fontSize = 12.sp
                            )
                            Text("Stored locally in Room database awaiting server upload", fontSize = 11.sp)
                        }
                        TextButton(onClick = onNavigateToHistory) {
                            Text("View", fontSize = 12.sp)
                        }
                    }
                }
            }

            // Identification Actions
            Text("Mosquito Specimen Actions", fontWeight = FontWeight.SemiBold, fontSize = 15.sp)

            // Screen 2 CTA: Adult Capture
            Button(
                onClick = onNavigateToAdultCapture,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(68.dp),
                shape = MaterialTheme.shapes.medium
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Start,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.Default.CameraAlt, contentDescription = null, modifier = Modifier.size(28.dp))
                    Spacer(modifier = Modifier.width(16.dp))
                    Column {
                        Text("Capture Adult Mosquito", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                        Text("High-Res Photo • Crop Specimen • Server AI Inference", fontSize = 11.sp, color = Color.White.copy(alpha = 0.85f))
                    }
                }
            }

            // Screen 6 CTA: Larvae Video
            OutlinedButton(
                onClick = onNavigateToLarvaeCapture,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(64.dp),
                shape = MaterialTheme.shapes.medium
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Start,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.Default.Videocam, contentDescription = null, modifier = Modifier.size(26.dp))
                    Spacer(modifier = Modifier.width(16.dp))
                    Column {
                        Text("Record Larvae Video", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                        Text("Strict 3–5s Clip • Meniscus Guide • Auto-stop at 5s", fontSize = 11.sp)
                    }
                }
            }

            // Metrics Summary
            Text("Device Collection Records", fontWeight = FontWeight.SemiBold, fontSize = 15.sp)

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
                        Text("$pendingUploadCount", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = if (pendingUploadCount > 0) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface)
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))
        }
    }
}
