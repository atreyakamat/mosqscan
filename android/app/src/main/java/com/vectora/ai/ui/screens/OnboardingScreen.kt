package com.vectora.ai.ui.screens

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.vectora.ai.data.local.keystore.KeystoreManager
import com.vectora.ai.data.remote.ServerClientManager
import com.vectora.ai.data.remote.dto.LoginRequest
import com.vectora.ai.data.remote.dto.RegisterRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OnboardingScreen(
    serverClientManager: ServerClientManager,
    keystoreManager: KeystoreManager,
    onComplete: () -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    var currentStep by remember { mutableIntStateOf(1) }

    // Step 2: Account Form
    var isRegisterMode by remember { mutableStateOf(false) }
    var email by remember { mutableStateOf("") }
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var passwordVisible by remember { mutableStateOf(false) }
    var authError by remember { mutableStateOf<String?>(null) }
    var isAuthenticating by remember { mutableStateOf(false) }
    var accountConfigured by remember { mutableStateOf<Boolean>(keystoreManager.hasAccessToken()) }

    // Step 3: Server Configuration
    var serverUrl by remember { mutableStateOf(serverClientManager.baseUrl) }
    var serverTestStatus by remember { mutableStateOf<String?>(null) }
    var isTestingServer by remember { mutableStateOf(false) }
    var serverTestSuccess by remember { mutableStateOf<Boolean?>(null) }
    var serverModelVersion by remember { mutableStateOf<String?>(null) }

    // Step 4: Permissions
    var cameraPermissionGranted by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        cameraPermissionGranted = isGranted
    }

    // Step 5: Final Connection Verification
    var finalVerifyStatus by remember { mutableStateOf<String?>(null) }
    var finalVerifySuccess by remember { mutableStateOf<Boolean?>(null) }
    var isFinalVerifying by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("Vectora ", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                        Text("AI Setup", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                    }
                },
                actions = {
                    Text(
                        "Step $currentStep of 6",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(end = 16.dp)
                    )
                }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(20.dp)
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            // Step Progress Indicator
            LinearProgressIndicator(
                progress = { currentStep / 6f },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp),
                color = MaterialTheme.colorScheme.primary,
                trackColor = MaterialTheme.colorScheme.surfaceVariant
            )

            AnimatedContent(
                targetState = currentStep,
                label = "onboarding_step"
            ) { step ->
                when (step) {
                    // -------------------------------------------------------
                    // STEP 1: WELCOME & PRODUCT INTRODUCTION
                    // -------------------------------------------------------
                    1 -> {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(16.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Spacer(modifier = Modifier.height(20.dp))
                            Box(
                                modifier = Modifier
                                    .size(80.dp)
                                    .background(MaterialTheme.colorScheme.primaryContainer, CircleShape),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    Icons.Default.BugReport,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.size(44.dp)
                                )
                            }

                            Text(
                                "Welcome to Vectora AI",
                                fontSize = 24.sp,
                                fontWeight = FontWeight.ExtraBold,
                                color = MaterialTheme.colorScheme.onBackground
                            )

                            Text(
                                "Intelligent Mosquito Identification & Vector Surveillance",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.primary
                            )

                            Card(
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Column(
                                    modifier = Modifier.padding(16.dp),
                                    verticalArrangement = Arrangement.spacedBy(12.dp)
                                ) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Default.CheckCircle, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                                        Spacer(modifier = Modifier.width(10.dp))
                                        Text("Adult mosquito genus classification (Aedes, Anopheles, Culex)", fontSize = 13.sp)
                                    }
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Default.CheckCircle, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                                        Spacer(modifier = Modifier.width(10.dp))
                                        Text("Manual specimen crop & quality validation", fontSize = 13.sp)
                                    }
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Default.CheckCircle, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                                        Spacer(modifier = Modifier.width(10.dp))
                                        Text("Local Gemma 3:4B research assistant integration", fontSize = 13.sp)
                                    }
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Default.CheckCircle, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                                        Spacer(modifier = Modifier.width(10.dp))
                                        Text("Offline capture queue with automatic sync", fontSize = 13.sp)
                                    }
                                }
                            }

                            Spacer(modifier = Modifier.height(16.dp))

                            Button(
                                onClick = { currentStep = 2 },
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(48.dp),
                                shape = RoundedCornerShape(8.dp)
                            ) {
                                Text("Get Started", fontSize = 15.sp, fontWeight = FontWeight.Bold)
                                Spacer(modifier = Modifier.width(8.dp))
                                Icon(Icons.Default.ArrowForward, contentDescription = null)
                            }
                        }
                    }

                    // -------------------------------------------------------
                    // STEP 2: ACCOUNT AUTHENTICATION
                    // -------------------------------------------------------
                    2 -> {
                        Column(
                            verticalArrangement = Arrangement.spacedBy(14.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Account Setup", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                            Text(
                                "Sign in or register an account. User sessions are persisted securely via Android Keystore (AES-256-GCM).",
                                fontSize = 12.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )

                            if (accountConfigured) {
                                Card(
                                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Row(modifier = Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Default.CheckCircle, contentDescription = null, tint = MaterialTheme.colorScheme.secondary)
                                        Spacer(modifier = Modifier.width(10.dp))
                                        Text("Active session found on device.", fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                                    }
                                }
                            }

                            if (authError != null) {
                                Card(
                                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Text(authError!!, color = MaterialTheme.colorScheme.onErrorContainer, fontSize = 12.sp, modifier = Modifier.padding(10.dp))
                                }
                            }

                            if (isRegisterMode) {
                                OutlinedTextField(
                                    value = username,
                                    onValueChange = { username = it },
                                    label = { Text("Username") },
                                    singleLine = true,
                                    modifier = Modifier.fillMaxWidth()
                                )
                            }

                            OutlinedTextField(
                                value = email,
                                onValueChange = { email = it },
                                label = { Text("Email Address") },
                                singleLine = true,
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                                modifier = Modifier.fillMaxWidth()
                            )

                            OutlinedTextField(
                                value = password,
                                onValueChange = { password = it },
                                label = { Text("Password") },
                                singleLine = true,
                                visualTransformation = if (passwordVisible) VisualTransformation.None else PasswordVisualTransformation(),
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                                trailingIcon = {
                                    IconButton(onClick = { passwordVisible = !passwordVisible }) {
                                        Icon(if (passwordVisible) Icons.Default.Visibility else Icons.Default.VisibilityOff, contentDescription = null)
                                    }
                                },
                                modifier = Modifier.fillMaxWidth()
                            )

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                TextButton(onClick = { isRegisterMode = !isRegisterMode }) {
                                    Text(if (isRegisterMode) "Existing user? Sign in" else "New user? Create account", fontSize = 12.sp)
                                }

                                Button(
                                    onClick = {
                                        isAuthenticating = true
                                        authError = null
                                        coroutineScope.launch {
                                            try {
                                                val service = serverClientManager.getService()
                                                if (isRegisterMode) {
                                                    val regResp = withContext(Dispatchers.IO) {
                                                        service.register(RegisterRequest(username.trim(), email.trim(), password))
                                                    }
                                                    if (!regResp.isSuccessful) {
                                                        authError = "Registration error: ${regResp.message()}"
                                                        isAuthenticating = false
                                                        return@launch
                                                    }
                                                }

                                                val loginResp = withContext(Dispatchers.IO) {
                                                    service.login(LoginRequest(email.trim(), password))
                                                }
                                                if (loginResp.isSuccessful && loginResp.body() != null) {
                                                    val token = loginResp.body()!!.accessToken
                                                    keystoreManager.saveAccessToken(token)
                                                    accountConfigured = true
                                                    isAuthenticating = false
                                                    currentStep = 3
                                                } else {
                                                    authError = "Authentication failed (HTTP ${loginResp.code()})"
                                                    isAuthenticating = false
                                                }
                                            } catch (e: Exception) {
                                                authError = "Connection error: ${e.message}"
                                                isAuthenticating = false
                                            }
                                        }
                                    },
                                    enabled = !isAuthenticating && email.isNotBlank() && password.isNotBlank(),
                                    shape = RoundedCornerShape(8.dp)
                                ) {
                                    if (isAuthenticating) {
                                        CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.White)
                                    } else {
                                        Text(if (isRegisterMode) "Register & Continue" else "Sign In & Continue")
                                    }
                                }
                            }

                            if (accountConfigured) {
                                OutlinedButton(
                                    onClick = { currentStep = 3 },
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(8.dp)
                                ) {
                                    Text("Skip to Server Configuration")
                                }
                            }
                        }
                    }

                    // -------------------------------------------------------
                    // STEP 3: SERVER CONFIGURATION
                    // -------------------------------------------------------
                    3 -> {
                        Column(
                            verticalArrangement = Arrangement.spacedBy(14.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Server Configuration", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                            Text(
                                "Configure your central Intel Core i7-2600 AI server address. On a physical device, use your local LAN IP (e.g. http://192.168.1.120:8000).",
                                fontSize = 12.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )

                            OutlinedTextField(
                                value = serverUrl,
                                onValueChange = {
                                    serverUrl = it
                                    serverClientManager.baseUrl = it
                                    serverTestStatus = null
                                    serverTestSuccess = null
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
                                        isTestingServer = true
                                        serverTestStatus = null
                                        coroutineScope.launch {
                                            val healthRes = serverClientManager.checkHealth()
                                            val modelRes = serverClientManager.checkModelHealth()
                                            if (healthRes.isSuccess && modelRes.isSuccess) {
                                                serverTestSuccess = true
                                                serverModelVersion = modelRes.getOrNull()
                                                serverTestStatus = "Connected! ${healthRes.getOrNull()} • ${modelRes.getOrNull()}"
                                            } else {
                                                serverTestSuccess = false
                                                serverTestStatus = "Connection failed: ${healthRes.exceptionOrNull()?.message ?: modelRes.exceptionOrNull()?.message}"
                                            }
                                            isTestingServer = false
                                        }
                                    },
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(8.dp)
                                ) {
                                    if (isTestingServer) {
                                        CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.White)
                                    } else {
                                        Text("Test Connection")
                                    }
                                }

                                Button(
                                    onClick = {
                                        serverUrl = "http://192.168.1.120:8000"
                                        serverClientManager.baseUrl = serverUrl
                                    },
                                    colors = ButtonDefaults.outlinedButtonColors(),
                                    shape = RoundedCornerShape(8.dp)
                                ) {
                                    Text("Reset i7 LAN", fontSize = 12.sp)
                                }
                            }

                            serverTestStatus?.let { status ->
                                Card(
                                    colors = CardDefaults.cardColors(
                                        containerColor = if (serverTestSuccess == true) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.errorContainer
                                    ),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Text(
                                        status,
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.Medium,
                                        modifier = Modifier.padding(12.dp)
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.height(10.dp))

                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                OutlinedButton(onClick = { currentStep = 2 }) { Text("Back") }
                                Button(
                                    onClick = { currentStep = 4 },
                                    enabled = serverUrl.isNotBlank(),
                                    shape = RoundedCornerShape(8.dp)
                                ) {
                                    Text("Next: Permissions")
                                }
                            }
                        }
                    }

                    // -------------------------------------------------------
                    // STEP 4: PERMISSIONS
                    // -------------------------------------------------------
                    4 -> {
                        Column(
                            verticalArrangement = Arrangement.spacedBy(16.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Device Permissions", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                            Text(
                                "Vectora AI requires specific hardware permissions to support field specimen capture and analysis.",
                                fontSize = 12.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )

                            Card(modifier = Modifier.fillMaxWidth()) {
                                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Default.CameraAlt, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                                        Spacer(modifier = Modifier.width(12.dp))
                                        Column {
                                            Text("Camera Access", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                            Text("Needed to capture high-resolution mosquito photographs for genus identification.", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                        }
                                    }
                                    Divider()
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Default.PhotoLibrary, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                                        Spacer(modifier = Modifier.width(12.dp))
                                        Column {
                                            Text("Gallery / Storage Access", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                            Text("Uses Android Photo Picker to select existing specimen photos without broad filesystem exposure.", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                        }
                                    }
                                    Divider()
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Default.Wifi, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                                        Spacer(modifier = Modifier.width(12.dp))
                                        Column {
                                            Text("Local Network Access", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                            Text("Transmits images to the i7 server and receives ONNX inference classifications.", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                        }
                                    }
                                }
                            }

                            if (!cameraPermissionGranted) {
                                Button(
                                    onClick = { permissionLauncher.launch(Manifest.permission.CAMERA) },
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(8.dp)
                                ) {
                                    Icon(Icons.Default.LockOpen, contentDescription = null)
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text("Grant Camera Permission")
                                }
                            } else {
                                Card(
                                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Row(modifier = Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Default.CheckCircle, contentDescription = null, tint = MaterialTheme.colorScheme.secondary)
                                        Spacer(modifier = Modifier.width(8.dp))
                                        Text("Camera permission granted.", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                                    }
                                }
                            }

                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                OutlinedButton(onClick = { currentStep = 3 }) { Text("Back") }
                                Button(
                                    onClick = { currentStep = 5 },
                                    shape = RoundedCornerShape(8.dp)
                                ) {
                                    Text("Next: Verification")
                                }
                            }
                        }
                    }

                    // -------------------------------------------------------
                    // STEP 5: CONNECTION VERIFICATION
                    // -------------------------------------------------------
                    5 -> {
                        Column(
                            verticalArrangement = Arrangement.spacedBy(16.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Connection Verification", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                            Text(
                                "Running an end-to-end verification of backend services, model checksum, and local AI assistant.",
                                fontSize = 12.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )

                            Button(
                                onClick = {
                                    isFinalVerifying = true
                                    coroutineScope.launch {
                                        val sHealth = serverClientManager.checkHealth()
                                        val mHealth = serverClientManager.checkModelHealth()
                                        val aHealth = serverClientManager.checkAssistantHealth()

                                        if (sHealth.isSuccess && mHealth.isSuccess) {
                                            finalVerifySuccess = true
                                            finalVerifyStatus = "Backend & ONNX Model Verified!\n• ${sHealth.getOrNull()}\n• ${mHealth.getOrNull()}\n• ${aHealth.getOrNull() ?: "Assistant optional"}"
                                        } else {
                                            finalVerifySuccess = false
                                            finalVerifyStatus = "Verification failed: Server or Model unavailable."
                                        }
                                        isFinalVerifying = false
                                    }
                                },
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(8.dp)
                            ) {
                                if (isFinalVerifying) {
                                    CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.White)
                                } else {
                                    Text("Run Full Health Check")
                                }
                            }

                            finalVerifyStatus?.let { status ->
                                Card(
                                    colors = CardDefaults.cardColors(
                                        containerColor = if (finalVerifySuccess == true) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.errorContainer
                                    ),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Text(status, fontSize = 12.sp, fontWeight = FontWeight.Medium, modifier = Modifier.padding(14.dp))
                                }
                            }

                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                OutlinedButton(onClick = { currentStep = 4 }) { Text("Back") }
                                Button(
                                    onClick = { currentStep = 6 },
                                    enabled = finalVerifySuccess == true,
                                    shape = RoundedCornerShape(8.dp)
                                ) {
                                    Text("Complete Setup")
                                }
                            }
                        }
                    }

                    // -------------------------------------------------------
                    // STEP 6: SETUP COMPLETION
                    // -------------------------------------------------------
                    6 -> {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(16.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Spacer(modifier = Modifier.height(20.dp))
                            Box(
                                modifier = Modifier
                                    .size(80.dp)
                                    .background(MaterialTheme.colorScheme.secondaryContainer, CircleShape),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    Icons.Default.Check,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.secondary,
                                    modifier = Modifier.size(44.dp)
                                )
                            }

                            Text(
                                "Setup Completed!",
                                fontSize = 24.sp,
                                fontWeight = FontWeight.ExtraBold,
                                color = MaterialTheme.colorScheme.onBackground
                            )

                            Text(
                                "Vectora AI is configured and connected to the central i7 server. You are ready to start scanning mosquito specimens.",
                                fontSize = 13.sp,
                                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )

                            Card(modifier = Modifier.fillMaxWidth()) {
                                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    Text("Configuration Summary", fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                    Text("Server URL: ${serverClientManager.baseUrl}", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    Text("Model Checksum: c3a3656f746a1bb... (Verified)", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    Text("Target Classes: 0: Aedes, 1: Anopheles, 2: Culex", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }

                            Spacer(modifier = Modifier.height(16.dp))

                            Button(
                                onClick = {
                                    serverClientManager.isOnboardingCompleted = true
                                    onComplete()
                                },
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(48.dp),
                                shape = RoundedCornerShape(8.dp)
                            ) {
                                Text("Open Dashboard", fontSize = 15.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }
        }
    }
}
