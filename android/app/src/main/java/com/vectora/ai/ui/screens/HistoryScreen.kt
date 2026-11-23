package com.vectora.ai.ui.screens

import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vectora.ai.data.local.db.SubmissionDao
import com.vectora.ai.data.local.db.SubmissionEntity
import kotlinx.coroutines.flow.collectLatest
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HistoryScreen(
    submissionDao: SubmissionDao,
    onBack: () -> Unit,
    onSelectSubmission: (String) -> Unit
) {
    var submissions by remember { mutableStateOf<List<SubmissionEntity>>(emptyList()) }
    var searchQuery by remember { mutableStateOf("") }
    var selectedGenusFilter by remember { mutableStateOf<String?>(null) } // null = all, "aedes", "anopheles", "culex", "uncertain", "pending"

    LaunchedEffect(Unit) {
        submissionDao.getAllSubmissions().collectLatest {
            submissions = it
        }
    }

    val filteredList = remember(submissions, searchQuery, selectedGenusFilter) {
        submissions.filter { item ->
            val matchesSearch = if (searchQuery.isBlank()) true else {
                val q = searchQuery.trim().lowercase()
                item.id.lowercase().contains(q) ||
                (item.predictedGenus?.lowercase()?.contains(q) == true) ||
                item.type.lowercase().contains(q)
            }

            val matchesFilter = when (selectedGenusFilter) {
                "aedes" -> item.predictedGenus?.lowercase() == "aedes"
                "anopheles" -> item.predictedGenus?.lowercase() == "anopheles"
                "culex" -> item.predictedGenus?.lowercase() == "culex"
                "uncertain" -> item.isUncertain
                "pending" -> item.status == "PENDING_UPLOAD" || !item.synced
                else -> true
            }

            matchesSearch && matchesFilter
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Scan History", fontSize = 18.sp, fontWeight = FontWeight.Bold) },
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
            // Search Input
            OutlinedTextField(
                value = searchQuery,
                onValueChange = { searchQuery = it },
                placeholder = { Text("Search by ID or genus...", fontSize = 13.sp) },
                leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                trailingIcon = {
                    if (searchQuery.isNotEmpty()) {
                        IconButton(onClick = { searchQuery = "" }) {
                            Icon(Icons.Default.Clear, contentDescription = "Clear")
                        }
                    }
                },
                singleLine = true,
                shape = RoundedCornerShape(10.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 6.dp)
            )

            // Filter Chips
            LazyRow(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 4.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                val filters = listOf(
                    null to "All (${submissions.size})",
                    "aedes" to "Aedes",
                    "anopheles" to "Anopheles",
                    "culex" to "Culex",
                    "uncertain" to "Uncertain",
                    "pending" to "Pending Upload"
                )

                items(filters) { (key, label) ->
                    FilterChip(
                        selected = selectedGenusFilter == key,
                        onClick = { selectedGenusFilter = if (selectedGenusFilter == key) null else key },
                        label = { Text(label, fontSize = 12.sp) }
                    )
                }
            }

            Divider(modifier = Modifier.padding(top = 4.dp))

            if (filteredList.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(
                            Icons.Default.SearchOff,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.size(48.dp)
                        )
                        Spacer(modifier = Modifier.height(10.dp))
                        Text("No matching specimen scans found.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            } else {
                LazyColumn(modifier = Modifier.fillMaxSize()) {
                    items(filteredList, key = { it.id }) { item ->
                        ListItem(
                            modifier = Modifier.clickable { onSelectSubmission(item.id) },
                            leadingContent = {
                                if (item.imagePath != null && File(item.imagePath).exists()) {
                                    val bmp = remember(item.imagePath) {
                                        BitmapFactory.decodeFile(item.imagePath)
                                    }
                                    if (bmp != null) {
                                        Image(
                                            bitmap = bmp.asImageBitmap(),
                                            contentDescription = "Specimen",
                                            contentScale = ContentScale.Crop,
                                            modifier = Modifier
                                                .size(52.dp)
                                                .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(8.dp))
                                        )
                                    } else {
                                        Box(
                                            modifier = Modifier
                                                .size(52.dp)
                                                .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(8.dp)),
                                            contentAlignment = Alignment.Center
                                        ) {
                                            Icon(Icons.Default.BugReport, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                                        }
                                    }
                                } else {
                                    Box(
                                        modifier = Modifier
                                            .size(52.dp)
                                            .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(8.dp)),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Icon(
                                            if (item.type == "adult") Icons.Default.BugReport else Icons.Default.Videocam,
                                            contentDescription = null,
                                            tint = MaterialTheme.colorScheme.primary
                                        )
                                    }
                                }
                            },
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
                                        fontWeight = FontWeight.SemiBold,
                                        fontSize = 14.sp
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
                                Text(
                                    "${df.format(Date(item.createdAt))} • $statusTxt",
                                    fontSize = 11.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            },
                            trailingContent = {
                                if (item.rawScore != null) {
                                    Text(
                                        String.format("%.1f%%", item.rawScore * 100),
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 13.sp,
                                        color = MaterialTheme.colorScheme.primary
                                    )
                                } else {
                                    Icon(Icons.Default.ChevronRight, contentDescription = null)
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
