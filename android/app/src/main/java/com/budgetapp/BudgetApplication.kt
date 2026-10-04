package com.budgetapp

import android.app.Application
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.budgetapp.data.local.AppDatabase
import com.budgetapp.data.repository.BudgetRepository
import com.budgetapp.workers.DailyRecurringWorker
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import java.util.concurrent.TimeUnit

class BudgetApplication : Application() {
    val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    val database by lazy { AppDatabase.getDatabase(this, applicationScope) }
    val repository by lazy { BudgetRepository(database) }

    override fun onCreate() {
        super.onCreate()
        setupBackgroundWorkers()
    }

    private fun setupBackgroundWorkers() {
        val recurringWorkRequest = PeriodicWorkRequestBuilder<DailyRecurringWorker>(
            12, TimeUnit.HOURS
        ).build()

        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "DailyRecurringCheck",
            ExistingPeriodicWorkPolicy.KEEP,
            recurringWorkRequest
        )
    }
}
