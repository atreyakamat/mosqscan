package com.vectora.ai.data.local.db

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(entities = [SubmissionEntity::class], version = 2, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun submissionDao(): SubmissionDao
}
