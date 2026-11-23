package com.vectora.ai.data.remote

import android.content.Context
import android.util.Log
import com.vectora.ai.data.local.keystore.KeystoreManager
import com.vectora.ai.data.remote.api.VectoraApiService
import com.vectora.ai.data.remote.interceptor.AuthInterceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

class ServerClientManager(
    private val context: Context,
    private val keystoreManager: KeystoreManager
) {
    companion object {
        private const val PREFS_NAME = "vectora_server_prefs"
        private const val KEY_SERVER_URL = "vectora_api_base_url"
        private const val KEY_ONBOARDING_COMPLETED = "vectora_onboarding_completed"
        private const val KEY_PERMISSION_SETUP_COMPLETED = "vectora_permission_setup_completed"
        val DEFAULT_SERVER_URL: String = com.vectora.ai.BuildConfig.API_BASE_URL
    }

    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    var isPermissionSetupCompleted: Boolean
        get() = prefs.getBoolean(KEY_PERMISSION_SETUP_COMPLETED, false)
        set(value) = prefs.edit().putBoolean(KEY_PERMISSION_SETUP_COMPLETED, value).apply()

    var isOnboardingCompleted: Boolean
        get() = prefs.getBoolean(KEY_ONBOARDING_COMPLETED, false)
        set(value) = prefs.edit().putBoolean(KEY_ONBOARDING_COMPLETED, value).apply()

    var baseUrl: String
        get() {
            val saved = prefs.getString(KEY_SERVER_URL, null)
            val base = if (!saved.isNullOrBlank()) saved else DEFAULT_SERVER_URL
            return if (!base.endsWith("/")) "$base/" else base
        }
        set(value) {
            val normalized = if (!value.endsWith("/")) "$value/" else value
            prefs.edit().putString(KEY_SERVER_URL, normalized).apply()
            rebuildClient()
        }

    private var cachedService: VectoraApiService? = null

    init {
        rebuildClient()
    }

    @Synchronized
    private fun rebuildClient() {
        try {
            val logging = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }

            val okHttpClient = OkHttpClient.Builder()
                .connectTimeout(20, TimeUnit.SECONDS)
                .readTimeout(180, TimeUnit.SECONDS)
                .writeTimeout(60, TimeUnit.SECONDS)
                .addInterceptor(AuthInterceptor(keystoreManager))
                .addInterceptor(logging)
                .build()

            val retrofit = Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()

            cachedService = retrofit.create(VectoraApiService::class.java)
        } catch (e: Exception) {
            Log.e("ServerClientManager", "Error building Retrofit client: ${e.message}", e)
        }
    }

    fun getService(): VectoraApiService {
        if (cachedService == null) {
            rebuildClient()
        }
        return cachedService!!
    }

    suspend fun checkHealth(): Result<String> {
        return try {
            val resp = getService().healthCheck()
            if (resp.isSuccessful) {
                Result.success("Server healthy (${resp.body()?.version ?: "2.0.0"})")
            } else {
                Result.failure(Exception("HTTP ${resp.code()}: ${resp.message()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun checkModelHealth(): Result<String> {
        return try {
            val resp = getService().modelHealth()
            if (resp.isSuccessful) {
                val body = resp.body()
                val statusMsg = "Model: ${body?.artifact} (verified=${body?.checksumVerified})"
                Result.success(statusMsg)
            } else {
                Result.failure(Exception("HTTP ${resp.code()}: ${resp.message()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun checkAssistantHealth(): Result<String> {
        return try {
            val resp = getService().assistantHealth()
            if (resp.isSuccessful) {
                val body = resp.body()
                if (body?.status == "healthy") {
                    Result.success("Gemma 3:4B Online (${body.targetModel})")
                } else {
                    Result.failure(Exception("Assistant: ${body?.status ?: "offline"}"))
                }
            } else {
                Result.failure(Exception("HTTP ${resp.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
