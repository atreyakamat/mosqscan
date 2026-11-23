package com.vectora.ai.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val DarkColorScheme = darkColorScheme(
    primary = VectoraTealLight,
    onPrimary = VectoraSlate900,
    primaryContainer = VectoraTealDark,
    onPrimaryContainer = VectoraTealLight,
    secondary = VectoraEmerald,
    onSecondary = Color.White,
    tertiary = VectoraAmber,
    background = VectoraSlate900,
    surface = VectoraSlate800,
    onBackground = VectoraSlate100,
    onSurface = VectoraSlate100,
    surfaceVariant = VectoraSlate700,
    onSurfaceVariant = VectoraSlate300,
    outline = VectoraSlate500,
    error = VectoraRose,
    errorContainer = Color(0xFF4C0519),
    onErrorContainer = VectoraRoseContainer
)

private val LightColorScheme = lightColorScheme(
    primary = VectoraTeal,
    onPrimary = Color.White,
    primaryContainer = VectoraTealContainer,
    onPrimaryContainer = VectoraTealDark,
    secondary = VectoraEmerald,
    onSecondary = Color.White,
    secondaryContainer = VectoraEmeraldContainer,
    tertiary = VectoraAmber,
    tertiaryContainer = VectoraAmberContainer,
    background = VectoraSlate50,
    surface = Color.White,
    onBackground = VectoraSlate900,
    onSurface = VectoraSlate900,
    surfaceVariant = VectoraSlate100,
    onSurfaceVariant = VectoraSlate500,
    outline = VectoraSlate200,
    error = VectoraRose,
    errorContainer = VectoraRoseContainer,
    onErrorContainer = Color(0xFF881337)
)

@Composable
fun VectoraAITheme(
    darkTheme: Boolean = false,
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
