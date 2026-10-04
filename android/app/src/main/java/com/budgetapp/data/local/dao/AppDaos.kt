package com.budgetapp.data.local.dao

import androidx.room.*
import com.budgetapp.data.local.entity.*
import kotlinx.coroutines.flow.Flow

@Dao
interface CategoryDao {
    @Query("SELECT * FROM categories ORDER BY name ASC")
    fun getAllCategories(): Flow<List<CategoryEntity>>

    @Query("SELECT * FROM categories ORDER BY name ASC")
    suspend fun getAllCategoriesSync(): List<CategoryEntity>

    @Query("SELECT * FROM categories WHERE id = :id LIMIT 1")
    suspend fun getCategoryById(id: Long): CategoryEntity?

    @Query("SELECT * FROM categories WHERE name = :name LIMIT 1")
    suspend fun getCategoryByName(name: String): CategoryEntity?

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertCategory(category: CategoryEntity): Long

    @Update
    suspend fun updateCategory(category: CategoryEntity)

    @Delete
    suspend fun deleteCategory(category: CategoryEntity)
}

@Dao
interface TransactionDao {
    @Query("SELECT * FROM transactions ORDER BY date DESC, id DESC")
    fun getAllTransactions(): Flow<List<TransactionEntity>>

    @Query("SELECT * FROM transactions ORDER BY date DESC, id DESC")
    suspend fun getAllTransactionsSync(): List<TransactionEntity>

    @Query("SELECT * FROM transactions WHERE date LIKE :monthPrefix || '%' ORDER BY date DESC, id DESC")
    fun getTransactionsForMonth(monthPrefix: String): Flow<List<TransactionEntity>>

    @Query("SELECT * FROM transactions WHERE date LIKE :monthPrefix || '%' ORDER BY date DESC, id DESC")
    suspend fun getTransactionsForMonthSync(monthPrefix: String): List<TransactionEntity>

    @Query("SELECT * FROM transactions WHERE status = 'pending_approval' ORDER BY date ASC")
    fun getPendingApprovalTransactions(): Flow<List<TransactionEntity>>

    @Query("SELECT * FROM transactions WHERE id = :id LIMIT 1")
    suspend fun getTransactionById(id: Long): TransactionEntity?

    @Query("SELECT * FROM transactions WHERE split_group_id = :splitGroupId ORDER BY id ASC")
    suspend fun getSplitTransactions(splitGroupId: String): List<TransactionEntity>

    @Query("""
        SELECT * FROM transactions 
        WHERE (description LIKE '%' || :query || '%')
        ORDER BY date DESC, id DESC
    """)
    fun searchTransactions(query: String): Flow<List<TransactionEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertTransaction(transaction: TransactionEntity): Long

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertTransactions(transactions: List<TransactionEntity>): List<Long>

    @Update
    suspend fun updateTransaction(transaction: TransactionEntity)

    @Delete
    suspend fun deleteTransaction(transaction: TransactionEntity)

    @Query("DELETE FROM transactions WHERE split_group_id = :splitGroupId")
    suspend fun deleteSplitGroup(splitGroupId: String)

    @Query("UPDATE transactions SET status = 'confirmed' WHERE id = :id")
    suspend fun approveTransaction(id: Long)

    @Query("SELECT DISTINCT SUBSTR(date, 1, 7) FROM transactions WHERE date IS NOT NULL ORDER BY date DESC")
    suspend fun getDistinctMonths(): List<String>
}

@Dao
interface RecurringTransactionDao {
    @Query("SELECT * FROM recurring_transactions WHERE active = 1 ORDER BY next_due_date ASC")
    fun getActiveRecurring(): Flow<List<RecurringTransactionEntity>>

    @Query("SELECT * FROM recurring_transactions WHERE active = 1 ORDER BY next_due_date ASC")
    suspend fun getActiveRecurringSync(): List<RecurringTransactionEntity>

    @Query("SELECT * FROM recurring_transactions ORDER BY next_due_date ASC")
    fun getAllRecurring(): Flow<List<RecurringTransactionEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertRecurring(recurring: RecurringTransactionEntity): Long

    @Update
    suspend fun updateRecurring(recurring: RecurringTransactionEntity)

    @Delete
    suspend fun deleteRecurring(recurring: RecurringTransactionEntity)
}

@Dao
interface EmergencyFundDao {
    @Query("SELECT * FROM emergency_fund LIMIT 1")
    fun getFund(): Flow<EmergencyFundEntity?>

    @Query("SELECT * FROM emergency_fund LIMIT 1")
    suspend fun getFundSync(): EmergencyFundEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun setFund(fund: EmergencyFundEntity)

    @Query("SELECT * FROM emergency_fund_log ORDER BY date DESC, id DESC")
    fun getLogs(): Flow<List<EmergencyFundLogEntity>>

    @Query("SELECT * FROM emergency_fund_log ORDER BY date DESC, id DESC")
    suspend fun getLogsSync(): List<EmergencyFundLogEntity>

    @Insert
    suspend fun insertLog(log: EmergencyFundLogEntity): Long
}

@Dao
interface SavingsDao {
    @Query("SELECT * FROM savings WHERE month = :month LIMIT 1")
    suspend fun getSavingsForMonth(month: String): SavingsEntity?

    @Query("SELECT * FROM savings ORDER BY month DESC")
    fun getAllSavings(): Flow<List<SavingsEntity>>

    @Query("SELECT * FROM savings ORDER BY month DESC")
    suspend fun getAllSavingsSync(): List<SavingsEntity>

    @Query("SELECT COALESCE(SUM(rollover_amount), 0) FROM savings")
    suspend fun getTotalSavingsBalance(): Double

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOrUpdate(savings: SavingsEntity)
}

@Dao
interface SavingsGoalDao {
    @Query("SELECT * FROM savings_goals ORDER BY is_completed ASC, created_at DESC")
    fun getAllGoals(): Flow<List<SavingsGoalEntity>>

    @Query("SELECT * FROM savings_goals WHERE is_completed = 0")
    suspend fun getActiveGoalsSync(): List<SavingsGoalEntity>

    @Query("SELECT * FROM savings_goals WHERE id = :id LIMIT 1")
    suspend fun getGoalById(id: Long): SavingsGoalEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertGoal(goal: SavingsGoalEntity): Long

    @Update
    suspend fun updateGoal(goal: SavingsGoalEntity)

    @Delete
    suspend fun deleteGoal(goal: SavingsGoalEntity)

    @Query("SELECT * FROM savings_goal_logs WHERE goal_id = :goalId ORDER BY date DESC, id DESC")
    fun getLogsForGoal(goalId: Long): Flow<List<SavingsGoalLogEntity>>

    @Insert
    suspend fun insertGoalLog(log: SavingsGoalLogEntity): Long
}

@Dao
interface SettingsDao {
    @Query("SELECT value FROM settings WHERE key = :key LIMIT 1")
    suspend fun getSetting(key: String): String?

    @Query("SELECT * FROM settings")
    fun getAllSettings(): Flow<List<SettingEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun setSetting(setting: SettingEntity)
}
