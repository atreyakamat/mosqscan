package com.vectora.ai.ui.screens

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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vectora.ai.data.local.keystore.KeystoreManager
import com.vectora.ai.data.remote.ServerClientManager
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onBack: () -> Unit,
    onNavigateToAuth: () -> Unit = {},
    keystoreManager: KeystoreManager? = null,
    serverClientManager: ServerClientManager? = null
) {
    val coroutineScope = rememberCoroutineScope()

    var serverUrlInput by remember {
        mutableStateOf(serverClientManager?.baseUrl ?: ServerClientManager.DEFAULT_SERVER_URL)
    }
    var connectionTestResult by remember { mutableStateOf<String?>(null) }
    var isTestingConnection by remember { mutableStateOf(false) }
    var connectionTestSuccess by remember { mutableStateOf<Boolean?>(null) }

    var modelHealthResult by remember { mutableStateOf<String?>(null) }
    var isCheckingModelHealth by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings & Server Config", fontSize = 18.sp, fontWeight = FontWeight.Bold) },
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
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Server Network Configuration Card
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Dns, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Vectora AI Inference Server", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    }
                    Divider()

                    Text(
                        "Configure the IP address or hostname of your central i7-2600 AI server.",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    OutlinedTextField(
                        value = serverUrlInput,
                        onValueChange = {
                            serverUrlInput = it
                            serverClientManager?.baseUrl = it
                            connectionTestResult = null
                            connectionTestSuccess = null
                        },
                        label = { Text("Server Base URL (VECTORa_API_BASE_URL)") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Button(
                            onClick = {
                                if (serverClientManager == null) return@Button
                                isTestingConnection = true
                                connectionTestResult = null
                                coroutineScope.launch {
                                    val result = serverClientManager.checkHealth()
                                    isTestingConnection = false
                                    if (result.isSuccess) {
                                        connectionTestSuccess = true
                                        connectionTestResult = result.getOrNull()
                                    } else {
                                        connectionTestSuccess = false
                                        connectionTestResult = result.exceptionOrNull()?.message ?: "Unreachable"
                                    }
                                }
                            },
                            enabled = !isTestingConnection,
                            modifier = Modifier.weight(1f)
                        ) {
                            if (isTestingConnection) {
                                CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.White)
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Testing...", fontSize = 12.sp)
                            } else {
                                Icon(Icons.Default.NetworkCheck, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Test Connection", fontSize = 12.sp)
                            }
                        }

                        OutlinedButton(
                            onClick = {
                                if (serverClientManager == null) return@OutlinedButton
                                isCheckingModelHealth = true
                                modelHealthResult = null
                                coroutineScope.launch {
                                    val result = serverClientManager.checkModelHealth()
                                    isCheckingModelHealth = false
                                    modelHealthResult = if (result.isSuccess) {
                                        result.getOrNull()
                                    } else {
                                        "Check failed: ${result.exceptionOrNull()?.message}"
                                    }
                                }
                            },
                            enabled = !isCheckingModelHealth,
                            modifier = Modifier.weight(1f)
                        ) {
                            if (isCheckingModelHealth) {
                                CircularProgressIndicator(modifier = Modifier.size(16.dp))
                            } else {
                                Text("Model Health", fontSize = 12.sp)
                            }
                        }
                    }

                    // Test Results Display
                    connectionTestResult?.let { res ->
                        Surface(
                            color = if (connectionTestSuccess == true) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.errorContainer,
                            shape = MaterialTheme.shapes.small,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(modifier = Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    if (connectionTestSuccess == true) Icons.Default.CheckCircle else Icons.Default.Error,
                                    contentDescription = null,
                                    tint = if (connectionTestSuccess == true) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                                    modifier = Modifier.size(18.dp)
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(res, fontSize = 12.sp)
                            }
                        }
                    }

                    modelHealthResult?.let { mRes ->
                        Surface(
                            color = MaterialTheme.colorScheme.secondaryContainer,
                            shape = MaterialTheme.shapes.small,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(mRes, fontSize = 11.sp, modifier = Modifier.padding(10.dp))
                        }
                    }
                }
            }

            // Server-Hosted AI Architecture Card
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Memory, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Active Server-Hosted AI Engine", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    }
                    Divider()

                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("Architecture", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("Remote Server Inference (CPU)", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                    }

                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("Host Processor", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("Intel Core i7-2600 (4C / 8T)", fontSize = 12.sp)
                    }

                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("Active Model", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("Exp B FP32 ONNX Candidate", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                    }

                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("Certainty Threshold", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("65% (Strict Heuristic)", fontSize = 12.sp)
                    }

                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("Model Status", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("EXPERIMENTAL_NOT_FIELD_VALIDATED", fontSize = 11.sp, color = MaterialTheme.colorScheme.error)
                    }
                }
            }

            // Authentication & Keystore Card
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Authentication & Keystore", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    Divider()

                    val hasToken = try {
                        keystoreManager?.getAccessToken() != null
                    } catch (_: Exception) {
                        false
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Account Status", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(
                            if (hasToken) "Authenticated" else "Guest / Unauthenticated",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = if (hasToken) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface
                        )
                    }

                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("Token Storage", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("Android Keystore (AES-256-GCM)", fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                    }

                    Spacer(modifier = Modifier.height(4.dp))
                    if (hasToken) {
                        OutlinedButton(
                            onClick = {
                                try {
                                    keystoreManager?.clearCredentials()
                                } catch (_: Exception) {}
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Sign Out (Clear Saved Token)")
                        }
                    } else {
                        Button(
                            onClick = onNavigateToAuth,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Sign In / Register")
                        }
                    }
                }
            }
        }
    }
}
