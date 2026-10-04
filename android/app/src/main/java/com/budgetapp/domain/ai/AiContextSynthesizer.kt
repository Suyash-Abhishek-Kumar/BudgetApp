package com.budgetapp.domain.ai

import com.budgetapp.data.local.entity.CategoryEntity
import com.budgetapp.data.local.entity.EmergencyFundEntity
import com.budgetapp.data.local.entity.SavingsGoalEntity
import com.budgetapp.data.local.entity.TransactionEntity
import com.budgetapp.domain.model.MonthlySummary
import java.time.LocalDate

object AiContextSynthesizer {

    fun buildFinancialContext(
        summary: MonthlySummary,
        categories: List<CategoryEntity>,
        transactions: List<TransactionEntity>,
        goals: List<SavingsGoalEntity>,
        emergencyFund: EmergencyFundEntity?,
        currencySymbol: String
    ): String {
        val sb = StringBuilder()
        val today = LocalDate.now().toString()

        sb.append("=== LIVE BUDGET CONTEXT (As of $today) ===\n")
        sb.append("Month: ${summary.month}\n")
        sb.append("Currency: $currencySymbol\n")
        sb.append(String.format("Monthly Income: %s%.2f\n", currencySymbol, summary.totalIncome))
        sb.append(String.format("Total Spent: %s%.2f\n", currencySymbol, summary.totalExpenses))
        sb.append(String.format("Available to Spend: %s%.2f\n", currencySymbol, summary.availableToSpend))
        sb.append(String.format("Emergency Fund Reserve: %s%.2f\n", currencySymbol, emergencyFund?.balance ?: 0.0))
        sb.append(String.format("Cumulative Savings Balance: %s%.2f\n", currencySymbol, summary.savingsBalance))

        summary.projection?.let { proj ->
            sb.append(String.format("Month-End Forecast: %s%.2f (Budget Cap: %s%.2f)\n", currencySymbol, proj.projectedMonthEndTotal, currencySymbol, proj.targetBudget))
        }

        sb.append("\n--- CATEGORY ENVELOPES ---\n")
        val catMap = categories.associateBy { it.id }
        summary.categorySummaries.forEach { cat ->
            val status = when {
                cat.isOverHardLimit -> "OVER HARD LIMIT ⚠️"
                cat.isOverSoftLimit -> "OVER SOFT LIMIT 🟡"
                else -> "HEALTHY ✅"
            }
            sb.append(
                String.format(
                    "• %s: Spent %s%.2f / Limit %s%.2f (%.0f%%) - %s\n",
                    cat.categoryName, currencySymbol, cat.spent, currencySymbol, cat.hardLimit, cat.percentageUsed, status
                )
            )
        }

        if (goals.isNotEmpty()) {
            sb.append("\n--- SAVINGS GOALS ---\n")
            goals.forEach { goal ->
                val progress = if (goal.targetAmount > 0) (goal.savedAmount / goal.targetAmount) * 100 else 0.0
                val targetDateStr = goal.targetDate?.let { " (Due: $it)" } ?: ""
                val statusStr = if (goal.isCompleted == 1) "COMPLETED 🎉" else String.format("%.0f%%", progress)
                sb.append(
                    String.format(
                        "• %s: %s%.2f / %s%.2f (%s)%s\n",
                        goal.name, currencySymbol, goal.savedAmount, currencySymbol, goal.targetAmount, statusStr, targetDateStr
                    )
                )
            }
        }

        sb.append("\n--- RECENT TRANSACTIONS (Latest 15) ---\n")
        val recent = transactions.take(15)
        recent.forEach { tx ->
            val catName = catMap[tx.categoryId]?.name ?: if (tx.type == "income") "Income" else "Uncategorized"
            val sign = if (tx.type == "income") "+" else "-"
            sb.append("• ${tx.date} | ${tx.description ?: catName} | $catName | $sign$currencySymbol${String.format("%.2f", tx.amount)}\n")
        }

        sb.append("\nINSTRUCTIONS: You are BudgetApp's personal financial copilot. Analyze the live budget context above to give concise, accurate, actionable advice. Never fabricate numbers outside the provided context.")
        return sb.toString()
    }
}
