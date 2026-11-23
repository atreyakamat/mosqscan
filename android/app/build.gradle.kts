import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.kapt)
    alias(libs.plugins.hilt.android)
    alias(libs.plugins.kotlin.serialization)
}

android {
    namespace = "com.vectora.ai"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.vectora.ai"
        minSdk = 29
        targetSdk = 34
        versionCode = 300
        versionName = "3.0.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        create("release") {
            val signingPropsFile = rootProject.file("signing.properties")
            val signingProps = Properties()
            if (signingPropsFile.exists()) {
                signingPropsFile.inputStream().use { signingProps.load(it) }
            }

            val keystorePath = signingProps.getProperty("VECTOR_KEYSTORE_PATH")
                ?: System.getenv("VECTOR_KEYSTORE_PATH")
                ?: project.findProperty("VECTOR_KEYSTORE_PATH")?.toString()
            val keystorePassword = signingProps.getProperty("VECTOR_KEYSTORE_PASSWORD")
                ?: System.getenv("VECTOR_KEYSTORE_PASSWORD")
                ?: project.findProperty("VECTOR_KEYSTORE_PASSWORD")?.toString()
            val keyAlias = signingProps.getProperty("VECTOR_KEY_ALIAS")
                ?: System.getenv("VECTOR_KEY_ALIAS")
                ?: project.findProperty("VECTOR_KEY_ALIAS")?.toString()
            val keyPassword = signingProps.getProperty("VECTOR_KEY_PASSWORD")
                ?: System.getenv("VECTOR_KEY_PASSWORD")
                ?: project.findProperty("VECTOR_KEY_PASSWORD")?.toString()

            if (!keystorePath.isNullOrBlank() && file(keystorePath).exists()) {
                storeFile = file(keystorePath)
                storePassword = keystorePassword
                this.keyAlias = keyAlias
                this.keyPassword = keyPassword
            }
        }
    }

    val defaultApiUrl = System.getenv("VECTORa_API_BASE_URL")
        ?: System.getenv("VECTORA_API_BASE_URL")
        ?: project.findProperty("VECTORa_API_BASE_URL")?.toString()
        ?: project.findProperty("VECTORA_API_BASE_URL")?.toString()
        ?: "http://192.168.1.120:8000"

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            buildConfigField("String", "API_BASE_URL", "\"$defaultApiUrl\"")
            val releaseSigning = signingConfigs.getByName("release")
            if (releaseSigning.storeFile != null && releaseSigning.storeFile!!.exists()) {
                signingConfig = releaseSigning
            }
        }
        debug {
            buildConfigField("String", "API_BASE_URL", "\"$defaultApiUrl\"")
        }
    }

    sourceSets {
        getByName("main") {
            assets.setSrcDirs(emptyList<String>())
        }
        getByName("debug") {
            assets.srcDirs("src/main/assets")
        }
        getByName("release") {
            assets.setSrcDirs(emptyList<String>())
        }
    }

    splits {
        abi {
            isEnable = true
            reset()
            include("armeabi-v7a", "arm64-v8a", "x86", "x86_64")
            isUniversalApk = true
        }
    }

    androidResources {
        noCompress += listOf("onnx")
    }


    buildFeatures {
        compose = true
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
        jniLibs {
            // Remove unneeded local ONNX Runtime Mobile binaries from remote client APK (~18.5 MB reduction)
            excludes += listOf("**/libonnxruntime.so", "**/libonnxruntime4j_jni.so")
        }
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)
    implementation(libs.androidx.material.icons.extended)

    // CameraX
    implementation(libs.androidx.camera.core)
    implementation(libs.androidx.camera.camera2)
    implementation(libs.androidx.camera.lifecycle)
    implementation(libs.androidx.camera.view)
    implementation(libs.androidx.camera.video)

    // Room
    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    kapt(libs.androidx.room.compiler)

    // Hilt
    implementation(libs.hilt.android)
    kapt(libs.hilt.compiler)
    implementation(libs.hilt.navigation.compose)

    // Navigation
    implementation(libs.androidx.navigation.compose)

    // Retrofit
    implementation(libs.retrofit)
    implementation(libs.retrofit.gson)
    implementation(libs.okhttp.logging)

    // ONNX Runtime
    implementation(libs.onnxruntime.android)

    // DataStore
    implementation(libs.androidx.datastore.preferences)

    // Biometric
    implementation(libs.androidx.biometric)

    // Coil
    implementation(libs.coil.compose)

    // Coroutines
    implementation(libs.kotlinx.coroutines.android)

    // Serialization
    implementation(libs.kotlinx.serialization.json)

    // Testing
    testImplementation(libs.junit)
    testImplementation(libs.mockk)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.ui.test.junit4)
    debugImplementation(libs.androidx.ui.tooling)
}
