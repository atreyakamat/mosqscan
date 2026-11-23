package com.vectora.ai.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.BugReport
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vectora.ai.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    onNavigateToAdultCapture: () -> Unit,
    onNavigateToLarvaeCapture: () -> Unit,
    onNavigateToSettings: (() -> Unit)? = null
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(36.dp)
                                .background(MaterialTheme.colorScheme.primaryContainer, RoundedCornerShape(8.dp)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.BugReport,
                                contentDescription = null,
                                tint = VectoraTeal,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                        Spacer(modifier = Modifier.width(10.dp))
                        Text("Vectora ", fontWeight = FontWeight.Bold, fontSize = 18.sp, color = VectoraSlate900)
                        Text("AI", fontWeight = FontWeight.Bold, fontSize = 18.sp, color = VectoraTeal)
                    }
                },
                actions = {
                    if (onNavigateToSettings != null) {
                        IconButton(onClick = onNavigateToSettings) {
                            Icon(
                                imageVector = Icons.Default.Settings,
                                contentDescription = "Settings",
                                tint = VectoraSlate500
                            )
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background
                )
            )
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(horizontal = 20.dp, vertical = 12.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            Spacer(modifier = Modifier.height(4.dp))

            // Main heading
            Column {
                Text(
                    text = "Choose what to scan",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = VectoraSlate900
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Select a specimen category to proceed with capture and analysis.",
                    fontSize = 13.sp,
                    color = VectoraSlate500
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Option 1: Adult Mosquito
            ScanOptionCard(
                title = "Adult Mosquito",
                description = "Identify an adult mosquito from a photograph.",
                icon = Icons.Default.BugReport,
                badgeText = null,
                onClick = onNavigateToAdultCapture
            )

            // Option 2: Mosquito Larvae
            ScanOptionCard(
                title = "Mosquito Larvae",
                description = "Capture or review mosquito larvae samples.",
                icon = Icons.Default.Videocam,
                badgeText = "Research only • Model not field-validated",
                onClick = onNavigateToLarvaeCapture
            )

            Spacer(modifier = Modifier.height(20.dp))
        }
    }
}

@Composable
private fun ScanOptionCard(
    title: String,
    description: String,
    icon: ImageVector,
    badgeText: String?,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(16.dp))
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top
            ) {
                Box(
                    modifier = Modifier
                        .size(56.dp)
                        .background(VectoraTealContainer, RoundedCornerShape(14.dp)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = icon,
                        contentDescription = null,
                        tint = VectoraTeal,
                        modifier = Modifier.size(30.dp)
                    )
                }

                if (badgeText != null) {
                    Surface(
                        color = VectoraAmberContainer,
                        shape = RoundedCornerShape(6.dp)
                    ) {
                        Text(
                            text = badgeText,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Medium,
                            color = VectoraAmber,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(18.dp))

            Text(
                text = title,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = VectoraSlate900
            )

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = description,
                fontSize = 13.sp,
                color = VectoraSlate500,
                lineHeight = 18.sp
            )

            Spacer(modifier = Modifier.height(16.dp))

            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Text(
                    text = "Open workflow",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = VectoraTeal
                )
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowForward,
                    contentDescription = null,
                    tint = VectoraTeal,
                    modifier = Modifier.size(16.dp)
                )
            }
        }
    }
}
