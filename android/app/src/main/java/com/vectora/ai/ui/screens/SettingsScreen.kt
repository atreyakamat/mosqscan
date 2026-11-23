package com.vectora.ai.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
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
import com.vectora.ai.data.local.keystore.KeystoreManager
import com.vectora.ai.data.remote.ServerClientManager
import com.vectora.ai.sync.SyncManager
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onBack: () -> Unit,
    onNavigateToAuth: () -> Unit = {},
    onNavigateToOnboarding: () -> Unit = {},
    keystoreManager: KeystoreManager? = null,
    serverClientManager: ServerClientManager? = null,
    submissionDao: SubmissionDao? = null
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

    var assistantHealthResult by remember { mutableStateOf<String?>(null) }
    var isCheckingAssistantHealth by remember { mutableStateOf(false) }

    var pendingUploadCount by remember { mutableIntStateOf(0) }
    var isSyncing by remember { mutableStateOf(false) }
    var syncResultText by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(submissionDao) {
        if (submissionDao != null) {
            val syncMgr = SyncManager(submissionDao)
            pendingUploadCount = syncMgr.getPendingSyncCount()
        }
    }

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
            // Account Section Card
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.AccountCircle, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("User Account", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    }
                    Divider()

                    val hasToken = keystoreManager?.hasAccessToken() == true
                    Text(
                        if (hasToken) "Active authenticated session. Tokens encrypted with Android Keystore."
                        else "No active session on this device. Sign in to sync your scans to the central database.",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        if (hasToken) {
                            OutlinedButton(
                                onClick = {
                                    keystoreManager?.clearTokens()
                                },
                                shape = RoundedCornerShape(8.dp)
                            ) {
                                Icon(Icons.Default.Logout, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                Text("Sign Out")
                            }
                        } else {
                            Button(
                                onClick = onNavigateToAuth,
                                shape = RoundedCornerShape(8.dp)
                            ) {
                                Icon(Icons.Default.Login, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                Text("Sign In / Register")
                            }
                        }

                        OutlinedButton(
                            onClick = onNavigateToOnboarding,
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Icon(Icons.Default.RestartAlt, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Re-run Setup Wizard")
                        }
                    }
                }
            }

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
                        "Configure the central i7-2600 AI server IP address or hostname. Physical tablets connect via LAN IP.",
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
                        label = { Text("Server Base URL") },
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
                                        connectionTestResult = "Failed: ${result.exceptionOrNull()?.message}"
                                    }
                                }
                            },
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.weight(1f)
                        ) {
                            if (isTestingConnection) {
                                CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.White)
                            } else {
                                Text("Test Connection")
                            }
                        }

                        Button(
                            onClick = {
                                serverUrlInput = "http://192.168.1.120:8000"
                                serverClientManager?.baseUrl = serverUrlInput
                                connectionTestResult = null
                                connectionTestSuccess = null
                            },
                            colors = ButtonDefaults.outlinedButtonColors(),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Text("Reset i7 LAN", fontSize = 12.sp)
                        }
                    }

                    connectionTestResult?.let { msg ->
                        Surface(
                            color = if (connectionTestSuccess == true) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.errorContainer,
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                msg,
                                fontSize = 12.sp,
                                modifier = Modifier.padding(10.dp),
                                color = if (connectionTestSuccess == true) MaterialTheme.colorScheme.onSecondaryContainer else MaterialTheme.colorScheme.onErrorContainer
                            )
                        }
                    }
                }
            }

            // Offline Sync Manager Card
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Sync, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Offline Queue & Synchronization", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    }
                    Divider()

                    Text(
                        "Pending offline uploads: $pendingUploadCount submission(s).",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    Button(
                        onClick = {
                            if (submissionDao == null || serverClientManager == null) return@Button
                            isSyncing = true
                            syncResultText = null
                            coroutineScope.launch {
                                val syncMgr = SyncManager(submissionDao)
                                val res = syncMgr.syncAllPending(serverClientManager)
                                pendingUploadCount = syncMgr.getPendingSyncCount()
                                isSyncing = false
                                syncResultText = "Sync completed: ${res.syncedCount} uploaded, ${res.failedCount} failed."
                            }
                        },
                        enabled = !isSyncing && pendingUploadCount > 0,
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        if (isSyncing) {
                            CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.White)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Syncing with i7 server...")
                        } else {
                            Icon(Icons.Default.CloudUpload, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Sync Now ($pendingUploadCount)")
                        }
                    }

                    syncResultText?.let { txt ->
                        Text(txt, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.primary)
                    }
                }
            }

            // Model Health & Checksum Verification Card
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Security, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Production Model Protection", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    }
                    Divider()

                    Text(
                        "Active Model: models/vectora_v3_fp32.onnx\n" +
                        "Expected SHA-256: c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa\n" +
                        "Class Mapping: 0: Aedes, 1: Anopheles, 2: Culex",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        lineHeight = 15.sp
                    )

                    Button(
                        onClick = {
                            if (serverClientManager == null) return@Button
                            isCheckingModelHealth = true
                            modelHealthResult = null
                            coroutineScope.launch {
                                val result = serverClientManager.checkModelHealth()
                                isCheckingModelHealth = false
                                modelHealthResult = if (result.isSuccess) {
                                    result.getOrNull()
                                } else {
                                    "Failed: ${result.exceptionOrNull()?.message}"
                                }
                            }
                        },
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        if (isCheckingModelHealth) {
                            CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.White)
                        } else {
                            Text("Verify Model Checksum via API")
                        }
                    }

                    modelHealthResult?.let { msg ->
                        Surface(
                            color = MaterialTheme.colorScheme.surfaceVariant,
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(msg, fontSize = 11.sp, modifier = Modifier.padding(10.dp))
                        }
                    }
                }
            }

            // Local AI Assistant Status Card
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Psychology, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Local AI Assistant (Gemma 3:4B)", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    }
                    Divider()

                    Text(
                        "Ollama service running on Intel Core i7-2600 host. Provides plain-language explanations of specimen scans.",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    Button(
                        onClick = {
                            if (serverClientManager == null) return@Button
                            isCheckingAssistantHealth = true
                            assistantHealthResult = null
                            coroutineScope.launch {
                                val result = serverClientManager.checkAssistantHealth()
                                isCheckingAssistantHealth = false
                                assistantHealthResult = if (result.isSuccess) {
                                    result.getOrNull()
                                } else {
                                    "Offline / Unavailable: ${result.exceptionOrNull()?.message}"
                                }
                            }
                        },
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        if (isCheckingAssistantHealth) {
                            CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.White)
                        } else {
                            Text("Check Gemma 3:4B Status")
                        }
                    }

                    assistantHealthResult?.let { res ->
                        Surface(
                            color = MaterialTheme.colorScheme.surfaceVariant,
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(res, fontSize = 11.sp, modifier = Modifier.padding(10.dp))
                        }
                    }
                }
            }

            // About & Disclaimers Card
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Application Information", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    Divider()
                    Text("Vectora AI Android Client v3.0.0 (Build 300)", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                    Text("Target Device: Samsung Galaxy Tab A7 Lite (SM-T225, Android 14)", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(
                        "Status: EXPERIMENTAL_NOT_FIELD_VALIDATED\n" +
                        "This application provides research-grade genus classification. It is not approved for clinical diagnostic, pathogen detection, or public health vector intervention deployment.",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        lineHeight = 14.sp
                    )
                }
            }

            Spacer(modifier = Modifier.height(20.dp))
        }
    }
}
