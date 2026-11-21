package com.vectora.ai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.vectora.ai.ui.navigation.VectoraNavGraph
import com.vectora.ai.ui.theme.VectoraAITheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            VectoraAITheme {
                VectoraNavGraph()
            }
        }
    }
}
