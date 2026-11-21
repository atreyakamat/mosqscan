package com.vectora.ai.data.remote.interceptor

import com.vectora.ai.data.local.keystore.KeystoreManager
import okhttp3.Interceptor
import okhttp3.Response

class AuthInterceptor(
    private val keystoreManager: KeystoreManager
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()
        val token = try {
            keystoreManager.getAccessToken()
        } catch (_: Exception) {
            null
        }

        val request = if (!token.isNullOrBlank()) {
            originalRequest.newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
        } else {
            originalRequest
        }

        return chain.proceed(request)
    }
}
