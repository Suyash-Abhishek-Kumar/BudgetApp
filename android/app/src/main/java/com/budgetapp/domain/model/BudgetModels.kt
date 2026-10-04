package com.budgetapp.domain.model

data class DailySpendPoint(
    val day: Int,
    val date: String,
    val dailySpent: Double,
    val cumulativeSpent: Double
)

data class ProjectionPoint(
    val day: Int,
    val date: String,
    val projectedCumulative: Double
)

data class MonthPaceProjection(
    val month: String,
    val daysInMonth: Int,
    val currentDay: Int,
    val actualSpending: List<DailySpendPoint>,
    val projectedSpending: List<ProjectionPoint>,
    val projectedMonthEndTotal: Double,
    val targetBudget: Double
)

data class CategorySpendSummary(
    val categoryId: Long,
    val categoryName: String,
    val spent: Double,
    val softLimit: Double,
    val hardLimit: Double,
    val percentageUsed: Double,
    val isOverSoftLimit: Boolean,
    val isOverHardLimit: Boolean
)

data class MonthlySummary(
    val month: String, // 'YYYY-MM'
    val totalIncome: Double,
    val totalExpenses: Double,
    val netSavings: Double,
    val availableToSpend: Double,
    val savingsBalance: Double,
    val emergencyFundBalance: Double,
    val isClosed: Boolean,
    val rolloverAmount: Double,
    val categorySummaries: List<CategorySpendSummary>,
    val projection: MonthPaceProjection? = null
)

data class HistoricalTrendPoint(
    val month: String, // 'YYYY-MM'
    val spent: Double,
    val rollover: Double
)

data class MonthArchiveRecord(
    val month: String, // 'YYYY-MM'
    val totalIncome: Double,
    val totalSpent: Double,
    val rolloverSavings: Double,
    val rolloverEf: Double,
    val totalSaved: Double
)

