package com.budgetapp.data.repository

import com.budgetapp.data.local.AppDatabase
import com.budgetapp.data.local.entity.*
import com.budgetapp.domain.calculator.BudgetCalculator
import com.budgetapp.domain.model.MonthlySummary
import kotlinx.coroutines.flow.Flow
import java.time.LocalDate

class BudgetRepository(private val db: AppDatabase) {

    // Category operations
    fun getAllCategories(): Flow<List<CategoryEntity>> = db.categoryDao().getAllCategories()
    suspend fun getAllCategoriesSync(): List<CategoryEntity> = db.categoryDao().getAllCategoriesSync()
    suspend fun insertCategory(category: CategoryEntity): Long = db.categoryDao().insertCategory(category)
    suspend fun updateCategory(category: CategoryEntity) = db.categoryDao().updateCategory(category)
    suspend fun deleteCategory(category: CategoryEntity) = db.categoryDao().deleteCategory(category)

    suspend fun transferCategoryBudget(fromId: Long, toId: Long, amount: Double, adjustSoft: Boolean = true) {
        val fromCat = db.categoryDao().getCategoryById(fromId) ?: throw IllegalArgumentException("Source category not found")
        val toCat = db.categoryDao().getCategoryById(toId) ?: throw IllegalArgumentException("Target category not found")

        if (fromCat.hardLimit < amount) {
            throw IllegalArgumentException("Insufficient limit in '${fromCat.name}' (limit: ${fromCat.hardLimit}, attempted: $amount)")
        }

        val newFromHard = kotlin.math.round((fromCat.hardLimit - amount) * 100.0) / 100.0
        val newFromSoft = if (adjustSoft && fromCat.hardLimit > 0) {
            val ratio = fromCat.softLimit / fromCat.hardLimit
            kotlin.math.round(newFromHard * ratio * 100.0) / 100.0
        } else {
            minOf(fromCat.softLimit, newFromHard)
        }

        val newToHard = kotlin.math.round((toCat.hardLimit + amount) * 100.0) / 100.0
        val newToSoft = if (adjustSoft && toCat.hardLimit > 0) {
            val ratio = toCat.softLimit / toCat.hardLimit
            kotlin.math.round(newToHard * ratio * 100.0) / 100.0
        } else {
            toCat.softLimit
        }

        db.categoryDao().updateCategory(fromCat.copy(softLimit = newFromSoft, hardLimit = newFromHard))
        db.categoryDao().updateCategory(toCat.copy(softLimit = newToSoft, hardLimit = newToHard))
    }

    // Transaction operations
    fun getAllTransactions(): Flow<List<TransactionEntity>> = db.transactionDao().getAllTransactions()
    fun getTransactionsForMonth(monthPrefix: String): Flow<List<TransactionEntity>> = db.transactionDao().getTransactionsForMonth(monthPrefix)
    fun getPendingApprovalTransactions(): Flow<List<TransactionEntity>> = db.transactionDao().getPendingApprovalTransactions()
    suspend fun insertTransaction(transaction: TransactionEntity): Long = db.transactionDao().insertTransaction(transaction)
    suspend fun insertTransactions(transactions: List<TransactionEntity>): List<Long> = db.transactionDao().insertTransactions(transactions)
    suspend fun updateTransaction(transaction: TransactionEntity) = db.transactionDao().updateTransaction(transaction)
    suspend fun deleteTransaction(transaction: TransactionEntity) = db.transactionDao().deleteTransaction(transaction)
    suspend fun approveTransaction(id: Long) = db.transactionDao().approveTransaction(id)
    suspend fun getDistinctMonths(): List<String> = db.transactionDao().getDistinctMonths()

    // Split Transactions
    suspend fun createSplitTransaction(
        date: String,
        description: String,
        splits: List<Pair<Long, Double>>, // categoryId to amount
        fundingSource: String = "regular"
    ) {
        val splitGroupId = java.util.UUID.randomUUID().toString()
        val txs = splits.map { (catId, amt) ->
            TransactionEntity(
                date = date,
                amount = amt,
                type = "expense",
                categoryId = catId,
                description = description,
                fundingSource = fundingSource,
                status = "confirmed",
                splitGroupId = splitGroupId
            )
        }
        db.transactionDao().insertTransactions(txs)
    }

    // Emergency Fund
    fun getEmergencyFund(): Flow<EmergencyFundEntity?> = db.emergencyFundDao().getFund()
    fun getEmergencyFundLogs(): Flow<List<EmergencyFundLogEntity>> = db.emergencyFundDao().getLogs()

    suspend fun depositEmergencyFund(amount: Double, note: String? = null) {
        val current = db.emergencyFundDao().getFundSync() ?: EmergencyFundEntity(balance = 0.0, lastUpdated = LocalDate.now().toString())
        val newBalance = current.balance + amount
        val now = LocalDate.now().toString()
        db.emergencyFundDao().setFund(current.copy(balance = newBalance, lastUpdated = now))
        db.emergencyFundDao().insertLog(
            EmergencyFundLogEntity(date = now, amount = amount, source = "manual", note = note)
        )
    }

    suspend fun withdrawEmergencyFund(amount: Double, note: String? = null) {
        val current = db.emergencyFundDao().getFundSync() ?: throw IllegalStateException("Emergency fund not initialized")
        if (current.balance < amount) throw IllegalArgumentException("Insufficient emergency fund balance")
        val newBalance = current.balance - amount
        val now = LocalDate.now().toString()
        db.emergencyFundDao().setFund(current.copy(balance = newBalance, lastUpdated = now))
        db.emergencyFundDao().insertLog(
            EmergencyFundLogEntity(date = now, amount = -amount, source = "manual", note = note)
        )
    }

    // Savings Goals
    fun getAllGoals(): Flow<List<SavingsGoalEntity>> = db.savingsGoalDao().getAllGoals()
    suspend fun insertGoal(goal: SavingsGoalEntity): Long = db.savingsGoalDao().insertGoal(goal)
    suspend fun updateGoal(goal: SavingsGoalEntity) = db.savingsGoalDao().updateGoal(goal)
    suspend fun deleteGoal(goal: SavingsGoalEntity) = db.savingsGoalDao().deleteGoal(goal)
    fun getGoalLogs(goalId: Long): Flow<List<SavingsGoalLogEntity>> = db.savingsGoalDao().getLogsForGoal(goalId)

    suspend fun contributeToGoal(goalId: Long, amount: Double, note: String? = null) {
        val goal = db.savingsGoalDao().getGoalById(goalId) ?: throw IllegalArgumentException("Goal not found")
        val newSaved = goal.savedAmount + amount
        val isCompleted = if (newSaved >= goal.targetAmount) 1 else 0
        db.savingsGoalDao().updateGoal(goal.copy(savedAmount = newSaved, isCompleted = isCompleted))
        db.savingsGoalDao().insertGoalLog(
            SavingsGoalLogEntity(
                goalId = goalId,
                date = LocalDate.now().toString(),
                amount = amount,
                type = "deposit",
                note = note,
                createdAt = java.time.Instant.now().toString()
            )
        )
    }

    // Recurring
    fun getAllRecurring(): Flow<List<RecurringTransactionEntity>> = db.recurringTransactionDao().getAllRecurring()
    suspend fun insertRecurring(recurring: RecurringTransactionEntity): Long = db.recurringTransactionDao().insertRecurring(recurring)
    suspend fun updateRecurring(recurring: RecurringTransactionEntity) = db.recurringTransactionDao().updateRecurring(recurring)
    suspend fun deleteRecurring(recurring: RecurringTransactionEntity) = db.recurringTransactionDao().deleteRecurring(recurring)

    // Savings & Rollover
    fun getAllSavings(): Flow<List<SavingsEntity>> = db.savingsDao().getAllSavings()
    suspend fun getAllSavingsSync(): List<SavingsEntity> = db.savingsDao().getAllSavingsSync()
    suspend fun getTotalSavingsBalance(): Double = db.savingsDao().getTotalSavingsBalance()

    suspend fun getClosedMonthsLedger(): List<com.budgetapp.domain.model.MonthArchiveRecord> {
        val closedSavings = db.savingsDao().getAllSavingsSync()
        return closedSavings.map { s ->
            val monthTxs = db.transactionDao().getTransactionsForMonthSync(s.month).filter { it.status == "confirmed" }
            val inc = monthTxs.filter { it.type == "income" }.sumOf { it.amount }
            val exp = monthTxs.filter { it.type == "expense" }.sumOf { it.amount }
            com.budgetapp.domain.model.MonthArchiveRecord(
                month = s.month,
                totalIncome = inc,
                totalSpent = exp,
                rolloverSavings = s.rolloverAmount,
                rolloverEf = s.emergencyFundDelta,
                totalSaved = s.rolloverAmount + s.emergencyFundDelta
            )
        }
    }

    suspend fun getHistoricalTrend(categoryId: Long? = null, monthsCount: Int = 6): List<com.budgetapp.domain.model.HistoricalTrendPoint> {
        val current = LocalDate.now()
        val months = mutableListOf<String>()
        var y = current.year
        var m = current.monthValue
        for (i in 0 until monthsCount) {
            months.add(String.format("%04d-%02d", y, m))
            m--
            if (m == 0) {
                m = 12
                y--
            }
        }
        months.reverse()

        val results = mutableListOf<com.budgetapp.domain.model.HistoricalTrendPoint>()
        for (monthStr in months) {
            val txs = db.transactionDao().getTransactionsForMonthSync(monthStr).filter { it.status == "confirmed" }
            val spent = if (categoryId == null) {
                txs.filter { it.type == "expense" }.sumOf { it.amount }
            } else {
                val exp = txs.filter { it.type == "expense" && it.categoryId == categoryId }.sumOf { it.amount }
                val inc = txs.filter { it.type == "income" && it.categoryId == categoryId }.sumOf { it.amount }
                maxOf(0.0, exp - inc)
            }

            val rollover = if (categoryId == null) {
                val s = db.savingsDao().getSavingsForMonth(monthStr)
                s?.rolloverAmount ?: 0.0
            } else {
                0.0
            }

            results.add(com.budgetapp.domain.model.HistoricalTrendPoint(month = monthStr, spent = spent, rollover = rollover))
        }
        return results
    }

    suspend fun autoRunAllPastRollovers(): List<String> {
        val allTx = db.transactionDao().getAllTransactionsSync()
        if (allTx.isEmpty()) return emptyList()

        val earliestDate = allTx.minOfOrNull { it.date } ?: return emptyList()
        val currentMonth = LocalDate.now().toString().substring(0, 7)

        val startY = earliestDate.substring(0, 4).toIntOrNull() ?: return emptyList()
        val startM = earliestDate.substring(5, 7).toIntOrNull() ?: return emptyList()
        val today = LocalDate.now()
        val endY = today.year
        val endM = today.monthValue

        val monthsToCheck = mutableListOf<String>()
        var y = startY
        var m = startM
        while (y < endY || (y == endY && m < endM)) {
            monthsToCheck.add(String.format("%04d-%02d", y, m))
            m++
            if (m > 12) {
                m = 1
                y++
            }
        }

        val categories = db.categoryDao().getAllCategoriesSync()
        val rolledOver = mutableListOf<String>()

        for (mStr in monthsToCheck) {
            val existing = db.savingsDao().getSavingsForMonth(mStr)
            if (existing == null) {
                // Compute month leftover
                val txs = db.transactionDao().getTransactionsForMonthSync(mStr).filter { it.status == "confirmed" }
                var totalLeftover = 0.0
                for (cat in categories) {
                    val catSpent = txs.filter { it.type == "expense" && it.categoryId == cat.id }.sumOf { it.amount }
                    val catInc = txs.filter { it.type == "income" && it.categoryId == cat.id }.sumOf { it.amount }
                    val netSpent = maxOf(0.0, catSpent - catInc)
                    val leftover = maxOf(0.0, cat.hardLimit - netSpent)
                    totalLeftover += leftover
                }

                // Emergency Fund split logic
                val efTarget = (getSetting("ef_target_amount") ?: "1000").toDoubleOrNull() ?: 1000.0
                val efContribType = getSetting("ef_monthly_contribution_type") ?: "fixed"
                val efContribVal = (getSetting("ef_monthly_contribution") ?: "50").toDoubleOrNull() ?: 50.0
                val efCurrent = db.emergencyFundDao().getFundSync()?.balance ?: 0.0

                var toEf = 0.0
                if (efCurrent < efTarget) {
                    val desired = if (efContribType == "percent") totalLeftover * (efContribVal / 100.0) else efContribVal
                    val room = efTarget - efCurrent
                    toEf = maxOf(0.0, minOf(desired, totalLeftover, room))
                }
                val toSavings = maxOf(0.0, totalLeftover - toEf)

                if (toEf > 0) {
                    depositEmergencyFund(toEf, "Automatic contribution for $mStr")
                }

                db.savingsDao().insertOrUpdate(
                    SavingsEntity(
                        month = mStr,
                        rolloverAmount = toSavings,
                        emergencyFundDelta = toEf
                    )
                )
                rolledOver.add(mStr)
            }
        }
        return rolledOver
    }

    // Settings
    suspend fun getSetting(key: String): String? = db.settingsDao().getSetting(key)
    suspend fun setSetting(key: String, value: String) = db.settingsDao().setSetting(SettingEntity(key = key, value = value))
    fun getAllSettings(): Flow<List<SettingEntity>> = db.settingsDao().getAllSettings()
}

