package com.budgetapp.domain.calculator

import com.budgetapp.data.local.entity.CategoryEntity
import com.budgetapp.data.local.entity.TransactionEntity
import com.budgetapp.domain.model.*
import java.time.LocalDate
import java.time.YearMonth

object BudgetCalculator {

    fun calculateMonthlySummary(
        month: String, // 'YYYY-MM'
        categories: List<CategoryEntity>,
        transactions: List<TransactionEntity>,
        savingsBalance: Double,
        emergencyFundBalance: Double,
        isClosed: Boolean = false,
        rolloverAmount: Double = 0.0,
        manualEfNetThisMonth: Double = 0.0
    ): MonthlySummary {
        val confirmedTx = transactions.filter { it.status == "confirmed" }

        val generalIncome = confirmedTx
            .filter { it.type == "income" && it.categoryId == null }
            .sumOf { it.amount }

        val categoryIncome = confirmedTx
            .filter { it.type == "income" && it.categoryId != null }
            .sumOf { it.amount }

        val totalIncome = generalIncome + categoryIncome

        val totalExpenses = confirmedTx
            .filter { it.type == "expense" }
            .sumOf { it.amount }

        // Category breakdown: net spent = expenses - category-specific supplement
        val categorySummaries = categories.map { cat ->
            val catExpenses = confirmedTx
                .filter { it.type == "expense" && it.categoryId == cat.id }
                .sumOf { it.amount }
            val catIncome = confirmedTx
                .filter { it.type == "income" && it.categoryId == cat.id }
                .sumOf { it.amount }
            val netSpent = maxOf(0.0, catExpenses - catIncome)

            val percentage = if (cat.hardLimit > 0) (netSpent / cat.hardLimit) * 100.0 else 0.0

            CategorySpendSummary(
                categoryId = cat.id,
                categoryName = cat.name,
                spent = netSpent,
                softLimit = cat.softLimit,
                hardLimit = cat.hardLimit,
                percentageUsed = percentage,
                isOverSoftLimit = netSpent > cat.softLimit,
                isOverHardLimit = netSpent > cat.hardLimit
            )
        }

        // Available to spend: Cash inflows minus expenses minus manual EF transfers
        val availableToSpend = generalIncome + categoryIncome - totalExpenses - manualEfNetThisMonth
        val netSavings = totalIncome - totalExpenses

        val projection = calculatePaceProjection(month, confirmedTx, categories.sumOf { it.hardLimit })

        return MonthlySummary(
            month = month,
            totalIncome = totalIncome,
            totalExpenses = totalExpenses,
            netSavings = netSavings,
            availableToSpend = availableToSpend,
            savingsBalance = savingsBalance,
            emergencyFundBalance = emergencyFundBalance,
            isClosed = isClosed,
            rolloverAmount = rolloverAmount,
            categorySummaries = categorySummaries,
            projection = projection
        )
    }

    fun calculatePaceProjection(
        month: String,
        confirmedTransactions: List<TransactionEntity>,
        targetBudget: Double
    ): MonthPaceProjection {
        val ym = try {
            YearMonth.parse(month)
        } catch (e: Exception) {
            YearMonth.now()
        }
        val daysInMonth = ym.lengthOfMonth()
        val today = LocalDate.now()
        val currentDay = if (today.toString().startsWith(month)) today.dayOfMonth else daysInMonth

        val dailyExpenses = confirmedTransactions
            .filter { it.type == "expense" }
            .groupBy {
                try {
                    LocalDate.parse(it.date).dayOfMonth
                } catch (e: Exception) {
                    1
                }
            }
            .mapValues { (_, txs) -> txs.sumOf { it.amount } }

        val actualPoints = mutableListOf<DailySpendPoint>()
        var running = 0.0
        for (d in 1..currentDay) {
            val daySpent = dailyExpenses[d] ?: 0.0
            running += daySpent
            actualPoints.add(
                DailySpendPoint(
                    day = d,
                    date = String.format("%s-%02d", month, d),
                    dailySpent = daySpent,
                    cumulativeSpent = running
                )
            )
        }

        val avgDailyRate = if (currentDay > 0) running / currentDay else 0.0
        val projectedPoints = mutableListOf<ProjectionPoint>()
        for (d in currentDay..daysInMonth) {
            val projected = running + (avgDailyRate * (d - currentDay))
            projectedPoints.add(
                ProjectionPoint(
                    day = d,
                    date = String.format("%s-%02d", month, d),
                    projectedCumulative = projected
                )
            )
        }

        val projectedEnd = projectedPoints.lastOrNull()?.projectedCumulative ?: running

        return MonthPaceProjection(
            month = month,
            daysInMonth = daysInMonth,
            currentDay = currentDay,
            actualSpending = actualPoints,
            projectedSpending = projectedPoints,
            projectedMonthEndTotal = projectedEnd,
            targetBudget = targetBudget
        )
    }
}
