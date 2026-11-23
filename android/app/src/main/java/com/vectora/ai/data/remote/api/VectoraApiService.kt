package com.vectora.ai.data.remote.api

import com.vectora.ai.data.remote.dto.*
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.*

interface VectoraApiService {

    @POST("api/v1/auth/login")
    suspend fun login(
        @Body request: LoginRequest
    ): Response<AuthResponse>

    @POST("api/v1/auth/register")
    suspend fun register(
        @Body request: RegisterRequest
    ): Response<UserDto>

    @GET("api/v1/auth/me")
    suspend fun getMe(): Response<UserDto>

    @GET("health")
    suspend fun healthCheck(): Response<HealthResponse>

    @GET("api/v1/models/health")
    suspend fun modelHealth(): Response<ModelHealthResponse>

    @Multipart
    @POST("api/v1/adult/submit")
    suspend fun submitAdult(
        @Part file: MultipartBody.Part,
        @Part("crop_x") cropX: RequestBody? = null,
        @Part("crop_y") cropY: RequestBody? = null,
        @Part("crop_w") cropW: RequestBody? = null,
        @Part("crop_h") cropH: RequestBody? = null
    ): Response<AdultSubmissionResponse>

    @GET("api/v1/adult/submissions/{id}")
    suspend fun getAdultSubmission(
        @Path("id") id: String
    ): Response<AdultSubmissionResponse>

    // Local Gemma 3:4B AI Assistant Endpoints
    @GET("api/v1/assistant/health")
    suspend fun assistantHealth(): Response<AssistantHealthResponse>

    @POST("api/v1/assistant/chat")
    suspend fun chatAssistant(
        @Body request: AssistantQueryRequest
    ): Response<AssistantResponse>

    @POST("api/v1/assistant/explain-result")
    suspend fun explainResult(
        @Body request: ExplainResultRequest
    ): Response<AssistantResponse>

    // Dashboard Statistics
    @GET("api/v1/dashboard/stats")
    suspend fun getDashboardStats(): Response<DashboardStatsDto>
}
