package com.vectora.ai.di

import android.content.Context
import com.vectora.ai.inference.OnnxAdultClassifier
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object InferenceModule {

    @Provides
    @Singleton
    fun provideAdultClassifier(@ApplicationContext context: Context): OnnxAdultClassifier {
        return OnnxAdultClassifier(context)
    }
}
