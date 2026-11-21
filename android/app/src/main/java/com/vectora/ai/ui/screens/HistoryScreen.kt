package com.vectora.ai.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vectora.ai.data.local.db.SubmissionDao
import com.vectora.ai.data.local.db.SubmissionEntity
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HistoryScreen(
    submissionDao: SubmissionDao,
    onBack: () -> Unit,
    onSelectSubmission: (String) -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    var submissions by remember { mutableStateOf<List<SubmissionEntity>>(emptyList()) }
    var selectedTab by remember { mutableIntStateOf(0) } // 0: All, 1: Adult, 2: Larvae

    LaunchedEffect(Unit) {
        submissionDao.getAllSubmissions().collectLatest {
            submissions = it
        }
    }

    val filteredList = when (selectedTab) {
        1 -> submissions.filter { it.type == "adult" }
        2 -> submissions.filter { it.type == "larvae" }
        else -> submissions
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Capture History", fontSize = 18.sp, fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            TabRow(selectedTabIndex = selectedTab) {
                Tab(selected = selectedTab == 0, onClick = { selectedTab = 0 }, text = { Text("All (${submissions.size})") })
                Tab(selected = selectedTab == 1, onClick = { selectedTab = 1 }, text = { Text("Adult") })
                Tab(selected = selectedTab == 2, onClick = { selectedTab = 2 }, text = { Text("Larvae") })
            }

            if (filteredList.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("No captures recorded in this category.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            } else {
                LazyColumn(modifier = Modifier.fillMaxSize()) {
                    items(filteredList, key = { it.id }) { item ->
                        ListItem(
                            modifier = Modifier.clickable { onSelectSubmission(item.id) },
                            headlineContent = {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(
                                        if (item.type == "adult") {
                                            if (item.status == "PENDING_UPLOAD" || !item.synced) "Pending Upload (Offline)"
                                            else if (item.isUncertain) "Uncertain Identification"
                                            else item.predictedGenus?.replaceFirstChar { it.uppercase() } ?: "Unknown Genus"
                                        } else {
                                            "Larvae Video Recording"
                                        },
                                        fontWeight = FontWeight.SemiBold
                                    )
                                    if (item.status == "PENDING_UPLOAD" || !item.synced) {
                                        Spacer(modifier = Modifier.width(6.dp))
                                        Badge(containerColor = MaterialTheme.colorScheme.tertiaryContainer) {
                                            Text("Pending", fontSize = 10.sp)
                                        }
                                    }
                                }
                            },
                            supportingContent = {
                                val df = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault())
                                val statusTxt = if (item.status == "PENDING_UPLOAD" || !item.synced) "Queued locally" else "Server verified"
                                Text("${item.type.replaceFirstChar { it.uppercase() }} • $statusTxt • ${df.format(Date(item.createdAt))}")
                            },
                            leadingContent = {
                                Icon(
                                    if (item.type == "adult") Icons.Default.CameraAlt else Icons.Default.Videocam,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.primary
                                )
                            },
                            trailingContent = {
                                IconButton(
                                    onClick = {
                                        coroutineScope.launch {
                                            submissionDao.deleteById(item.id)
                                        }
                                    }
                                ) {
                                    Icon(Icons.Default.Delete, contentDescription = "Delete", tint = MaterialTheme.colorScheme.error)
                                }
                            }
                        )
                        Divider()
                    }
                }
            }
        }
    }
}
