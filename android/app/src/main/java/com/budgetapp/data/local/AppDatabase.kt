package com.budgetapp.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.sqlite.db.SupportSQLiteDatabase
import com.budgetapp.data.local.dao.*
import com.budgetapp.data.local.entity.*
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

@Database(
    entities = [
        CategoryEntity::class,
        TransactionEntity::class,
        SavingsEntity::class,
        SettingEntity::class,
        EmergencyFundEntity::class,
        EmergencyFundLogEntity::class,
        RecurringTransactionEntity::class,
        SavingsGoalEntity::class,
        SavingsGoalLogEntity::class
    ],
    version = 4,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {

    abstract fun categoryDao(): CategoryDao
    abstract fun transactionDao(): TransactionDao
    abstract fun recurringTransactionDao(): RecurringTransactionDao
    abstract fun emergencyFundDao(): EmergencyFundDao
    abstract fun savingsDao(): SavingsDao
    abstract fun savingsGoalDao(): SavingsGoalDao
    abstract fun settingsDao(): SettingsDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getDatabase(context: Context, scope: CoroutineScope): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "budget.db"
                )
                    .fallbackToDestructiveMigration()
                    .addCallback(AppDatabaseCallback(scope))
                    .build()
                INSTANCE = instance
                instance
            }
        }

        private class AppDatabaseCallback(
            private val scope: CoroutineScope
        ) : RoomDatabase.Callback() {
            override fun onCreate(db: SupportSQLiteDatabase) {
                super.onCreate(db)
                INSTANCE?.let { database ->
                    scope.launch(Dispatchers.IO) {
                        populateInitialData(database)
                    }
                }
            }

            private suspend fun populateInitialData(db: AppDatabase) {
                val now = java.time.LocalDate.now().toString()

                val defaultCategories = listOf(
                    CategoryEntity(name = "Housing", softLimit = 1200.0, hardLimit = 1500.0, createdAt = now),
                    CategoryEntity(name = "Groceries", softLimit = 400.0, hardLimit = 500.0, createdAt = now),
                    CategoryEntity(name = "Utilities", softLimit = 200.0, hardLimit = 250.0, createdAt = now),
                    CategoryEntity(name = "Dining Out", softLimit = 150.0, hardLimit = 200.0, createdAt = now),
                    CategoryEntity(name = "Entertainment", softLimit = 100.0, hardLimit = 150.0, createdAt = now),
                    CategoryEntity(name = "Transportation", softLimit = 150.0, hardLimit = 200.0, createdAt = now),
                    CategoryEntity(name = "Healthcare", softLimit = 100.0, hardLimit = 150.0, createdAt = now),
                    CategoryEntity(name = "Personal", softLimit = 100.0, hardLimit = 150.0, createdAt = now)
                )
                defaultCategories.forEach { db.categoryDao().insertCategory(it) }

                db.emergencyFundDao().setFund(
                    EmergencyFundEntity(id = 1, balance = 0.0, lastUpdated = now)
                )

                db.settingsDao().setSetting(SettingEntity(key = "currency_symbol", value = "$"))
                db.settingsDao().setSetting(SettingEntity(key = "theme", value = "system"))
                db.settingsDao().setSetting(SettingEntity(key = "privacy_mode", value = "0"))
                db.settingsDao().setSetting(SettingEntity(key = "ef_target_amount", value = "5000.0"))
                db.settingsDao().setSetting(SettingEntity(key = "ef_monthly_contribution_type", value = "percent"))
                db.settingsDao().setSetting(SettingEntity(key = "ef_monthly_contribution", value = "20.0"))
                db.settingsDao().setSetting(SettingEntity(key = "gemini_model", value = "gemini-1.5-flash"))
            }
        }
    }
}
