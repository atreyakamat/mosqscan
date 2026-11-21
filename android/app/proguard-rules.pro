# ONNX Runtime JNI Reflection Rules
-keep class ai.onnxruntime.** { *; }
-dontwarn ai.onnxruntime.**

# Room and SQLite
-keep class androidx.room.** { *; }
-dontwarn androidx.room.**

# Retrofit and Gson
-keepattributes Signature, InnerClasses, EnclosingMethod
-keepclassmembers,allowobfuscation class * {
    @com.google.gson.annotations.SerializedName <fields>;
}

# Kotlin Serialization
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.SerializationKt
-keepclassmembers class * {
    *** Companion;
}
-keepclasseswithmembers class * {
    kotlinx.serialization.KSerializer serializer(...);
}

# Vectora AI models & inference
-keep class com.vectora.ai.domain.model.** { *; }
-keep class com.vectora.ai.data.remote.dto.** { *; }
-keep class com.vectora.ai.data.local.db.** { *; }
-keep class com.vectora.ai.inference.** { *; }
