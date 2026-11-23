package com.vectora.ai.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
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
import com.vectora.ai.data.remote.ServerClientManager
import com.vectora.ai.data.remote.dto.AssistantQueryRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class ChatMessage(
    val sender: String, // "user" or "assistant"
    val content: String,
    val timestamp: Long = System.currentTimeMillis()
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AssistantScreen(
    serverClientManager: ServerClientManager,
    onBack: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    val listState = rememberLazyListState()

    var messages by remember {
        mutableStateOf(
            listOf(
                ChatMessage(
                    sender = "assistant",
                    content = "Hello! I am the Vectora AI Technical Research Assistant, powered by Gemma 3:4B on your local i7 host. I can help explain mosquito morphology, genus differences (*Aedes*, *Anopheles*, *Culex*), and interpret specimen scan results."
                )
            )
        )
    }

    var inputText by remember { mutableStateOf("") }
    var isSending by remember { mutableStateOf(false) }
    var assistantAvailable by remember { mutableStateOf<Boolean?>(null) }
    var statusMessage by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        val check = serverClientManager.checkAssistantHealth()
        if (check.isSuccess) {
            assistantAvailable = true
            statusMessage = check.getOrNull()
        } else {
            assistantAvailable = false
            statusMessage = "Local Gemma 3:4B assistant is offline. Normal scanning continues working."
        }
    }

    fun sendMessage(text: String) {
        val query = text.trim()
        if (query.isBlank() || isSending) return

        messages = messages + ChatMessage(sender = "user", content = query)
        inputText = ""
        isSending = true

        coroutineScope.launch {
            try {
                val service = serverClientManager.getService()
                val resp = withContext(Dispatchers.IO) {
                    service.chatAssistant(AssistantQueryRequest(prompt = query))
                }

                if (resp.isSuccessful && resp.body() != null) {
                    val reply = resp.body()!!.response
                    messages = messages + ChatMessage(sender = "assistant", content = reply)
                } else {
                    val err = resp.body()?.error ?: "Server error HTTP ${resp.code()}"
                    messages = messages + ChatMessage(
                        sender = "assistant",
                        content = "Could not generate response: $err. Check if Ollama is running on the host."
                    )
                }
            } catch (e: Exception) {
                messages = messages + ChatMessage(
                    sender = "assistant",
                    content = "Connection to local AI assistant failed: ${e.message}"
                )
            } finally {
                isSending = false
                listState.animateScrollToItem(messages.size - 1)
            }
        }
    }

    val promptSuggestions = listOf(
        "Explain Aedes characteristics",
        "Culex vs Anopheles identification",
        "Explain mosquito anatomy",
        "What does uncalibrated score mean?"
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("Vectora ", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                            Text("AI Assistant", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                        }
                        Text(
                            if (assistantAvailable == true) "Gemma 3:4B • Local CPU Inference" else "Assistant Offline",
                            fontSize = 11.sp,
                            color = if (assistantAvailable == true) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
                        )
                    }
                },
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
            // Assistant Offline Warning Banner
            if (assistantAvailable == false) {
                Surface(
                    color = MaterialTheme.colorScheme.errorContainer,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Info, contentDescription = null, tint = MaterialTheme.colorScheme.error, modifier = Modifier.size(20.dp))
                        Spacer(modifier = Modifier.width(10.dp))
                        Text(
                            "Vectora AI Assistant is currently offline. Your mosquito identification result remains available.",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onErrorContainer
                        )
                    }
                }
            }

            // Chat Messages List
            LazyColumn(
                state = listState,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                items(messages) { msg ->
                    val isAssistant = msg.sender == "assistant"
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = if (isAssistant) Arrangement.Start else Arrangement.End
                    ) {
                        if (isAssistant) {
                            Box(
                                modifier = Modifier
                                    .size(32.dp)
                                    .background(MaterialTheme.colorScheme.primaryContainer, CircleShape),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(Icons.Default.Psychology, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(18.dp))
                            }
                            Spacer(modifier = Modifier.width(8.dp))
                        }

                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = if (isAssistant) MaterialTheme.colorScheme.surfaceVariant else MaterialTheme.colorScheme.primary,
                            contentColor = if (isAssistant) MaterialTheme.colorScheme.onSurfaceVariant else Color.White,
                            modifier = Modifier.widthIn(max = 300.dp)
                        ) {
                            Text(
                                text = msg.content,
                                fontSize = 13.sp,
                                lineHeight = 18.sp,
                                modifier = Modifier.padding(12.dp)
                            )
                        }
                    }
                }

                if (isSending) {
                    item {
                        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(8.dp)) {
                            CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Gemma 3:4B is thinking on i7 CPU...", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }

            // Quick Prompt Suggestions
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 4.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                promptSuggestions.take(2).forEach { suggestion ->
                    SuggestionChip(
                        onClick = { sendMessage(suggestion) },
                        label = { Text(suggestion, fontSize = 11.sp) },
                        shape = RoundedCornerShape(16.dp)
                    )
                }
            }

            // Input Row
            Surface(
                tonalElevation = 2.dp,
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    OutlinedTextField(
                        value = inputText,
                        onValueChange = { inputText = it },
                        placeholder = { Text("Ask Gemma about mosquitoes...", fontSize = 13.sp) },
                        singleLine = true,
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(24.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    IconButton(
                        onClick = { sendMessage(inputText) },
                        enabled = !isSending && inputText.isNotBlank(),
                        modifier = Modifier
                            .background(
                                if (inputText.isNotBlank()) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant,
                                CircleShape
                            )
                    ) {
                        Icon(
                            Icons.Default.Send,
                            contentDescription = "Send",
                            tint = if (inputText.isNotBlank()) Color.White else MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }
}
