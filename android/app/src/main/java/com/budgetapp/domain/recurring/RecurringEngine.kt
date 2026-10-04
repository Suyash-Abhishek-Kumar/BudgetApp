package com.budgetapp.domain.recurring

import com.budgetapp.data.local.dao.RecurringTransactionDao
import com.budgetapp.data.local.dao.TransactionDao
import com.budgetapp.data.local.entity.RecurringTransactionEntity
import com.budgetapp.data.local.entity.TransactionEntity
import java.time.LocalDate

class RecurringEngine(
    private val recurringDao: RecurringTransactionDao,
    private val transactionDao: TransactionDao
) {
    suspend fun processDueRecurring(today: LocalDate = LocalDate.now()): Int {
        val activeRules = recurringDao.getActiveRecurringSync()
        var stagedCount = 0

        for (rule in activeRules) {
            val dueDate = try {
                LocalDate.parse(rule.nextDueDate)
            } catch (e: Exception) {
                continue
            }

            if (!dueDate.isAfter(today)) {
                val stagedTx = TransactionEntity(
                    date = dueDate.toString(),
                    amount = rule.amount,
                    type = rule.type,
                    categoryId = rule.categoryId,
                    description = rule.description ?: "Recurring: ${rule.frequency}",
                    fundingSource = "regular",
                    recurringId = rule.id,
                    status = "pending_approval"
                )
                transactionDao.insertTransaction(stagedTx)
                stagedCount++

                val nextDate = computeNextDueDate(dueDate, rule.frequency, rule.intervalDays)
                recurringDao.updateRecurring(rule.copy(nextDueDate = nextDate.toString()))
            }
        }
        return stagedCount
    }

    private fun computeNextDueDate(current: LocalDate, frequency: String, intervalDays: Int?): LocalDate {
        return when (frequency.lowercase()) {
            "daily" -> current.plusDays(1)
            "monthly" -> current.plusMonths(1)
            "yearly" -> current.plusYears(1)
            "custom" -> current.plusDays((intervalDays ?: 1).toLong())
            else -> current.plusMonths(1)
        }
    }
}

