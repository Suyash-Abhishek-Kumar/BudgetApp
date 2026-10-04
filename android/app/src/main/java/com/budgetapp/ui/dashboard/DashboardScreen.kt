package com.budgetapp.ui.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.budgetapp.domain.model.CategorySpendSummary
import com.budgetapp.domain.model.MonthlySummary
import com.budgetapp.ui.theme.*

@Composable
fun DashboardScreen(
    summary: MonthlySummary,
    historicalTrend: List<com.budgetapp.domain.model.HistoricalTrendPoint> = emptyList(),
    currencySymbol: String = "$",
    isPrivacyMode: Boolean = false,
    isArchiveMonth: Boolean = false,
    onOpenReallocate: () -> Unit,
    modifier: Modifier = Modifier
) {
    var selectedCategoryId by remember { mutableStateOf<Long?>(null) }
    val selectedCatName = summary.categorySummaries.find { it.categoryId == selectedCategoryId }?.categoryName

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Archive Read-Only Warning Banner
        if (isArchiveMonth) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(8.dp),
                    colors = CardDefaults.cardColors(containerColor = AmberWarning.copy(alpha = 0.2f))
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(Icons.Default.Info, contentDescription = null, tint = AmberWarning)
                        Text(
                            text = "Time Machine Mode: Viewing past archived month (${summary.month}). New transactions apply to the current active month.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }
                }
            }
        }

        // Summary KPI Cards Grid
        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    MetricCard(
                        title = "Available to Spend",
                        value = summary.availableToSpend,
                        currency = currencySymbol,
                        isPrivacy = isPrivacyMode,
                        color = PrimaryBlue,
                        modifier = Modifier.weight(1f)
                    )
                    MetricCard(
                        title = "Total Spent",
                        value = summary.totalExpenses,
                        currency = currencySymbol,
                        isPrivacy = isPrivacyMode,
                        color = AmberWarning,
                        modifier = Modifier.weight(1f)
                    )
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    MetricCard(
                        title = "Monthly Income",
                        value = summary.totalIncome,
                        currency = currencySymbol,
                        isPrivacy = isPrivacyMode,
                        color = GreenSuccess,
                        modifier = Modifier.weight(1f)
                    )
                    MetricCard(
                        title = "Emergency Fund",
                        value = summary.emergencyFundBalance,
                        currency = currencySymbol,
                        isPrivacy = isPrivacyMode,
                        color = PurpleAccent,
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }

        // Spending Pace & Forecast Chart (With explicit X and Y coordinates)
        summary.projection?.let { proj ->
            item {
                SpendingPaceChart(projection = proj, currencySymbol = currencySymbol)
            }
        }

        // True Filled Pie Chart with Wedge Slices and Percentage Labels
        item {
            CategorySpendingPieChart(
                categories = summary.categorySummaries,
                currencySymbol = currencySymbol,
                selectedCategoryId = selectedCategoryId,
                onSelectCategory = { selectedCategoryId = it }
            )
        }

        // 6-Month Historical Spending Trend Chart
        item {
            MonthlySpendingTrendChart(
                trendData = historicalTrend,
                currencySymbol = currencySymbol,
                selectedCategoryName = selectedCatName
            )
        }

        // Category Budgets Header with Reallocate Button
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Category Budgets",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.SemiBold
                )

                FilledTonalButton(
                    onClick = onOpenReallocate,
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                ) {
                    Icon(Icons.Default.SwapHoriz, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Reallocate", style = MaterialTheme.typography.labelSmall)
                }
            }
        }

        // Category Budgets List
        items(summary.categorySummaries) { cat ->
            CategoryProgressCard(cat = cat, currency = currencySymbol, isPrivacy = isPrivacyMode)
        }
    }
}

@Composable
fun MetricCard(
    title: String,
    value: Double,
    currency: String,
    isPrivacy: Boolean,
    color: Color,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        border = CardDefaults.outlinedCardBorder(),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(8.dp)
                        .clip(RoundedCornerShape(2.dp))
                        .background(color)
                )
                Text(
                    text = title,
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Medium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f),
                    maxLines = 1
                )
            }
            val displayValue = if (isPrivacy) "••••••" else String.format("%s%.2f", currency, value)
            Text(
                text = displayValue,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = color,
                maxLines = 1
            )
        }
    }
}

@Composable
fun CategoryProgressCard(
    cat: CategorySpendSummary,
    currency: String,
    isPrivacy: Boolean,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        border = CardDefaults.outlinedCardBorder(),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = cat.categoryName,
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.SemiBold
                )
                val statusText = if (isPrivacy) "••••" else String.format(
                    "%s%.0f / %s%.0f",
                    currency, cat.spent, currency, cat.hardLimit
                )
                Text(
                    text = statusText,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = when {
                        cat.isOverHardLimit -> RedDanger
                        cat.isOverSoftLimit -> AmberWarning
                        else -> MaterialTheme.colorScheme.onSurface.copy(alpha = 0.75f)
                    }
                )
            }

            val progressFraction = (cat.spent / maxOf(1.0, cat.hardLimit)).toFloat().coerceIn(0f, 1f)
            val barColor = when {
                cat.isOverHardLimit -> RedDanger
                cat.isOverSoftLimit -> AmberWarning
                else -> PrimaryBlue
            }

            LinearProgressIndicator(
                progress = { progressFraction },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp)),
                color = barColor,
                trackColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f),
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = String.format("Soft: %s%.0f", currency, cat.softLimit),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                )
                Text(
                    text = String.format("Hard: %s%.0f", currency, cat.hardLimit),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                )
            }
        }
    }
}
