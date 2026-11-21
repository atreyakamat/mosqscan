package com.vectora.ai.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val DarkColorScheme = darkColorScheme(
    primary = VectoraGreenLight,
    secondary = VectoraTeal,
    tertiary = VectoraAmber
)

private val LightColorScheme = lightColorScheme(
    primary = VectoraGreen,
    secondary = VectoraTeal,
    tertiary = VectoraAmber
)

@Composable
fun VectoraAITheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
