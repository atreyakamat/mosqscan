package com.vectora.ai.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vectora.ai.data.local.keystore.KeystoreManager
import com.vectora.ai.data.remote.ServerClientManager
import com.vectora.ai.data.remote.dto.LoginRequest
import com.vectora.ai.data.remote.dto.RegisterRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AuthScreen(
    keystoreManager: KeystoreManager,
    serverClientManager: ServerClientManager? = null,
    onBack: () -> Unit,
    onAuthSuccess: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()

    var isRegisterMode by remember { mutableStateOf(false) }
    var email by remember { mutableStateOf("") }
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var passwordVisible by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var isSubmitting by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(if (isRegisterMode) "Create Account" else "Sign In", fontSize = 18.sp, fontWeight = FontWeight.Bold) },
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
                .padding(24.dp)
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Icon(
                Icons.Default.Lock,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(48.dp)
            )

            Text(
                if (isRegisterMode) "Register on Vectora Server" else "Sign in to Vectora Server",
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold
            )

            Text(
                "Connecting to: ${serverClientManager?.baseUrl ?: ServerClientManager.DEFAULT_SERVER_URL}\nTokens are encrypted via Android Keystore (AES-256-GCM).",
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            errorMessage?.let { error ->
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        error,
                        color = MaterialTheme.colorScheme.onErrorContainer,
                        fontSize = 13.sp,
                        modifier = Modifier.padding(12.dp)
                    )
                }
            }

            OutlinedTextField(
                value = email,
                onValueChange = { email = it; errorMessage = null },
                label = { Text("Email Address") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                modifier = Modifier.fillMaxWidth()
            )

            if (isRegisterMode) {
                OutlinedTextField(
                    value = username,
                    onValueChange = { username = it; errorMessage = null },
                    label = { Text("Username") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }

            OutlinedTextField(
                value = password,
                onValueChange = { password = it; errorMessage = null },
                label = { Text("Password") },
                singleLine = true,
                visualTransformation = if (passwordVisible) VisualTransformation.None else PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                trailingIcon = {
                    IconButton(onClick = { passwordVisible = !passwordVisible }) {
                        Icon(
                            if (passwordVisible) Icons.Default.Visibility else Icons.Default.VisibilityOff,
                            contentDescription = "Toggle password visibility"
                        )
                    }
                },
                modifier = Modifier.fillMaxWidth()
            )

            Button(
                onClick = {
                    if (email.isBlank() || password.isBlank() || (isRegisterMode && username.isBlank())) {
                        errorMessage = "All fields are required."
                        return@Button
                    }
                    if (password.length < 8) {
                        errorMessage = "Password must be at least 8 characters."
                        return@Button
                    }

                    isSubmitting = true
                    coroutineScope.launch {
                        try {
                            val service = serverClientManager?.getService()
                            if (service == null) {
                                errorMessage = "Network service unavailable."
                                isSubmitting = false
                                return@launch
                            }

                            if (isRegisterMode) {
                                val regResp = withContext(Dispatchers.IO) {
                                    service.register(RegisterRequest(username = username.trim(), email = email.trim(), password = password))
                                }
                                if (!regResp.isSuccessful) {
                                    val err = regResp.errorBody()?.string() ?: "Registration failed (${regResp.code()})"
                                    errorMessage = err
                                    isSubmitting = false
                                    return@launch
                                }
                            }

                            // Perform Login
                            val loginResp = withContext(Dispatchers.IO) {
                                service.login(LoginRequest(email = email.trim(), password = password))
                            }

                            if (loginResp.isSuccessful && loginResp.body() != null) {
                                val token = loginResp.body()!!.accessToken
                                keystoreManager.saveAccessToken(token)
                                isSubmitting = false
                                onAuthSuccess()
                            } else {
                                val err = loginResp.errorBody()?.string() ?: "Authentication failed (${loginResp.code()})"
                                errorMessage = err
                                isSubmitting = false
                            }
                        } catch (e: Exception) {
                            errorMessage = "Connection error: ${e.message}"
                            isSubmitting = false
                        }
                    }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(50.dp),
                enabled = !isSubmitting
            ) {
                if (isSubmitting) {
                    CircularProgressIndicator(modifier = Modifier.size(20.dp), color = MaterialTheme.colorScheme.onPrimary)
                } else {
                    Text(if (isRegisterMode) "Register" else "Sign In")
                }
            }

            TextButton(
                onClick = {
                    isRegisterMode = !isRegisterMode
                    errorMessage = null
                }
            ) {
                Text(
                    if (isRegisterMode) "Already have an account? Sign In" else "Need an account? Register"
                )
            }
        }
    }
}
