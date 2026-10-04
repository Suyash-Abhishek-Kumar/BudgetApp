package com.budgetapp.workers

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.budgetapp.data.local.AppDatabase
import com.budgetapp.domain.recurring.RecurringEngine
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class DailyRecurringWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            val db = AppDatabase.getDatabase(applicationContext, CoroutineScope(Dispatchers.IO))
            val engine = RecurringEngine(
                recurringDao = db.recurringTransactionDao(),
                transactionDao = db.transactionDao()
            )
            engine.processDueRecurring()
            Result.success()
        } catch (_: Exception) {
            Result.retry()
        }
    }
}
