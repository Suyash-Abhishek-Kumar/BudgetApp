package com.budgetapp.ui.dashboard

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.budgetapp.domain.model.CategorySpendSummary
import com.budgetapp.domain.model.HistoricalTrendPoint
import com.budgetapp.domain.model.MonthPaceProjection
import com.budgetapp.ui.theme.*
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin

val ChartPalette = listOf(
    PrimaryBlue, AmberWarning, GreenSuccess, PurpleAccent,
    Color(0xFFEC4899), Color(0xFF06B6D4), Color(0xFF84CC16), Color(0xFFF97316),
    Color(0xFF14B8A6), Color(0xFF6366F1), Color(0xFFE11D48), Color(0xFF8B5CF6)
)

@Composable
fun SpendingPaceChart(
    projection: MonthPaceProjection,
    currencySymbol: String = "$",
    modifier: Modifier = Modifier
) {
    var selectedDayPoint by remember { mutableStateOf<Pair<Int, Double>?>(null) }
    val density = LocalDensity.current

    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = CardDefaults.outlinedCardBorder(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Spending Pace & Forecast",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                Surface(
                    color = if (projection.projectedMonthEndTotal > projection.targetBudget && projection.targetBudget > 0) RedContainer else BrandBlueContainer,
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(
                        text = String.format("Forecast: %s%.0f", currencySymbol, projection.projectedMonthEndTotal),
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = if (projection.projectedMonthEndTotal > projection.targetBudget && projection.targetBudget > 0) RedDanger else BrandBlueDark,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = String.format("Monthly Budget Limit: %s%.0f", currencySymbol, projection.targetBudget),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                )
                if (selectedDayPoint != null) {
                    Text(
                        text = String.format("Day %d: %s%.2f", selectedDayPoint!!.first, currencySymbol, selectedDayPoint!!.second),
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = PrimaryBlue
                    )
                }
            }

            // Canvas Line Chart with Explicit X and Y Axes & Numeric Labels
            val maxY = maxOf(projection.targetBudget * 1.15, projection.projectedMonthEndTotal * 1.15, 100.0).toFloat()
            val totalDays = projection.daysInMonth.toFloat()
            val gridColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f)
            val axisColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.35f)
            val textColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)

            val leftPaddingPx = with(density) { 54.dp.toPx() }
            val bottomPaddingPx = with(density) { 30.dp.toPx() }
            val topPaddingPx = with(density) { 16.dp.toPx() }
            val rightPaddingPx = with(density) { 14.dp.toPx() }
            val labelTextSizePx = with(density) { 11.sp.toPx() }

            Canvas(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(210.dp)
                    .pointerInput(projection) {
                        detectTapGestures { offset ->
                            val chartW = size.width - leftPaddingPx - rightPaddingPx
                            if (offset.x >= leftPaddingPx && offset.x <= size.width - rightPaddingPx) {
                                val frac = (offset.x - leftPaddingPx) / chartW
                                val day = (frac * (totalDays - 1) + 1).toInt().coerceIn(1, projection.daysInMonth)
                                val match = projection.actualSpending.find { it.day == day }
                                    ?: projection.projectedSpending.find { it.day == day }?.let {
                                        com.budgetapp.domain.model.DailySpendPoint(it.day, it.date, 0.0, it.projectedCumulative)
                                    }
                                if (match != null) {
                                    selectedDayPoint = Pair(day, match.cumulativeSpent)
                                }
                            }
                        }
                    }
            ) {
                val chartW = size.width - leftPaddingPx - rightPaddingPx
                val chartH = size.height - bottomPaddingPx - topPaddingPx

                fun getX(day: Int): Float = leftPaddingPx + ((day - 1) / (totalDays - 1).coerceAtLeast(1f)) * chartW
                fun getY(value: Double): Float = topPaddingPx + (chartH - ((value.toFloat() / maxY) * chartH)).coerceIn(0f, chartH)

                // 1. Draw Y-Axis Horizontal Grid Lines and Labels
                val ySteps = 4
                for (i in 0..ySteps) {
                    val yVal = (maxY / ySteps) * i
                    val yPos = getY(yVal.toDouble())

                    // Horizontal grid line
                    drawLine(
                        color = gridColor,
                        start = Offset(leftPaddingPx, yPos),
                        end = Offset(size.width - rightPaddingPx, yPos),
                        strokeWidth = 1.dp.toPx(),
                        pathEffect = PathEffect.dashPathEffect(floatArrayOf(6f, 6f), 0f)
                    )

                    // Y-axis numeric label
                    drawContext.canvas.nativeCanvas.apply {
                        val paint = android.graphics.Paint().apply {
                            color = android.graphics.Color.argb(
                                (textColor.alpha * 255).toInt(),
                                (textColor.red * 255).toInt(),
                                (textColor.green * 255).toInt(),
                                (textColor.blue * 255).toInt()
                            )
                            textSize = labelTextSizePx
                            textAlign = android.graphics.Paint.Align.RIGHT
                            isAntiAlias = true
                        }
                        val labelText = String.format("%s%.0f", currencySymbol, yVal)
                        drawText(labelText, leftPaddingPx - 10f, yPos + (labelTextSizePx / 3f), paint)
                    }
                }

                // 2. Draw X-Axis Ticks & Labels (Day 1, 10, 20, End)
                val xDays = listOf(1, 10, 20, projection.daysInMonth)
                xDays.forEach { d ->
                    val xPos = getX(d)
                    drawLine(
                        color = axisColor,
                        start = Offset(xPos, size.height - bottomPaddingPx),
                        end = Offset(xPos, size.height - bottomPaddingPx + 8f),
                        strokeWidth = 1.5f
                    )

                    drawContext.canvas.nativeCanvas.apply {
                        val paint = android.graphics.Paint().apply {
                            color = android.graphics.Color.argb(
                                (textColor.alpha * 255).toInt(),
                                (textColor.red * 255).toInt(),
                                (textColor.green * 255).toInt(),
                                (textColor.blue * 255).toInt()
                            )
                            textSize = labelTextSizePx
                            textAlign = android.graphics.Paint.Align.CENTER
                            isAntiAlias = true
                        }
                        drawText("D$d", xPos, size.height - bottomPaddingPx + labelTextSizePx + 8f, paint)
                    }
                }

                // 3. Draw Solid X and Y Axes Baselines
                // Y-Axis line
                drawLine(
                    color = axisColor,
                    start = Offset(leftPaddingPx, topPaddingPx),
                    end = Offset(leftPaddingPx, size.height - bottomPaddingPx),
                    strokeWidth = 2.dp.toPx()
                )
                // X-Axis line
                drawLine(
                    color = axisColor,
                    start = Offset(leftPaddingPx, size.height - bottomPaddingPx),
                    end = Offset(size.width - rightPaddingPx, size.height - bottomPaddingPx),
                    strokeWidth = 2.dp.toPx()
                )

                // 4. Target Budget Horizontal Guideline
                if (projection.targetBudget > 0) {
                    val budgetY = getY(projection.targetBudget)
                    drawLine(
                        color = RedDanger.copy(alpha = 0.7f),
                        start = Offset(leftPaddingPx, budgetY),
                        end = Offset(size.width - rightPaddingPx, budgetY),
                        strokeWidth = 2.dp.toPx(),
                        pathEffect = PathEffect.dashPathEffect(floatArrayOf(10f, 10f), 0f)
                    )
                }

                // 5. Ideal Linear Pace Line
                if (projection.targetBudget > 0) {
                    drawLine(
                        color = Color.Gray.copy(alpha = 0.4f),
                        start = Offset(getX(1), getY(0.0)),
                        end = Offset(getX(projection.daysInMonth), getY(projection.targetBudget)),
                        strokeWidth = 1.5.dp.toPx(),
                        pathEffect = PathEffect.dashPathEffect(floatArrayOf(6f, 6f), 0f)
                    )
                }

                // 6. Actual Spending Path
                val actual = projection.actualSpending
                if (actual.isNotEmpty()) {
                    val actualPath = Path()
                    actualPath.moveTo(getX(actual.first().day), getY(actual.first().cumulativeSpent))
                    for (i in 1 until actual.size) {
                        actualPath.lineTo(getX(actual[i].day), getY(actual[i].cumulativeSpent))
                    }
                    drawPath(
                        path = actualPath,
                        color = PrimaryBlue,
                        style = Stroke(width = 3.dp.toPx())
                    )

                    actual.forEach { pt ->
                        drawCircle(
                            color = PrimaryBlue,
                            radius = 3.dp.toPx(),
                            center = Offset(getX(pt.day), getY(pt.cumulativeSpent))
                        )
                    }
                }

                // 7. Projected Spending Path (Dashed)
                val proj = projection.projectedSpending
                if (proj.isNotEmpty()) {
                    val projPath = Path()
                    projPath.moveTo(getX(proj.first().day), getY(proj.first().projectedCumulative))
                    for (i in 1 until proj.size) {
                        projPath.lineTo(getX(proj[i].day), getY(proj[i].projectedCumulative))
                    }
                    drawPath(
                        path = projPath,
                        color = AmberWarning,
                        style = Stroke(
                            width = 2.5.dp.toPx(),
                            pathEffect = PathEffect.dashPathEffect(floatArrayOf(10f, 8f), 0f)
                        )
                    )
                }
            }

            // Legend
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                LegendIndicator(color = PrimaryBlue, label = "Actual Spend")
                LegendIndicator(color = AmberWarning, label = "Projected")
                LegendIndicator(color = Color.Red.copy(alpha = 0.7f), label = "Budget Cap")
            }
        }
    }
}

@Composable
fun CategorySpendingPieChart(
    categories: List<CategorySpendSummary>,
    currencySymbol: String = "$",
    selectedCategoryId: Long? = null,
    onSelectCategory: (Long?) -> Unit = {},
    modifier: Modifier = Modifier
) {
    val totalSpent = categories.sumOf { it.spent }
    val activeCategories = categories.filter { it.spent > 0 }
    val density = LocalDensity.current

    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = CardDefaults.outlinedCardBorder(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Spending Breakdown",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                if (selectedCategoryId != null) {
                    FilledTonalButton(
                        onClick = { onSelectCategory(null) },
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 2.dp),
                        modifier = Modifier.height(28.dp)
                    ) {
                        Text("Reset Filter", style = MaterialTheme.typography.labelSmall)
                    }
                }
            }

            if (totalSpent <= 0 || activeCategories.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(130.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text("No expenses recorded this month", color = Slate400, style = MaterialTheme.typography.bodyMedium)
                }
            } else {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Donut / Pie Chart with Center Stats
                    Box(
                        modifier = Modifier
                            .size(136.dp)
                            .pointerInput(activeCategories, totalSpent) {
                                detectTapGestures { tapOffset ->
                                    val center = Offset(size.width / 2f, size.height / 2f)
                                    val dx = tapOffset.x - center.x
                                    val dy = tapOffset.y - center.y
                                    var angle = Math.toDegrees(atan2(dy.toDouble(), dx.toDouble())).toFloat()
                                    if (angle < 0) angle += 360f

                                    // Rotate angle by +90 because slices start at -90 (top)
                                    val normalizedAngle = (angle + 90f) % 360f

                                    var curSweep = 0f
                                    for (cat in activeCategories) {
                                        val sweep = ((cat.spent / totalSpent) * 360f).toFloat()
                                        if (normalizedAngle >= curSweep && normalizedAngle <= curSweep + sweep) {
                                            if (selectedCategoryId == cat.categoryId) {
                                                onSelectCategory(null)
                                            } else {
                                                onSelectCategory(cat.categoryId)
                                            }
                                            break
                                        }
                                        curSweep += sweep
                                    }
                                }
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Canvas(modifier = Modifier.fillMaxSize()) {
                            var startAngle = -90f
                            val center = Offset(size.width / 2f, size.height / 2f)
                            val outerRadius = size.minDimension / 2f
                            val strokeWidthPx = outerRadius * 0.42f

                            activeCategories.forEachIndexed { i, cat ->
                                val sweep = ((cat.spent / totalSpent) * 360f).toFloat()
                                val color = ChartPalette[i % ChartPalette.size]
                                val isSelected = selectedCategoryId == cat.categoryId

                                drawArc(
                                    color = if (selectedCategoryId == null || isSelected) color else color.copy(alpha = 0.25f),
                                    startAngle = startAngle,
                                    sweepAngle = sweep,
                                    useCenter = false,
                                    topLeft = Offset(strokeWidthPx / 2f, strokeWidthPx / 2f),
                                    size = Size(size.width - strokeWidthPx, size.height - strokeWidthPx),
                                    style = Stroke(width = strokeWidthPx)
                                )

                                startAngle += sweep
                            }
                        }

                        // Center callout displaying total spent
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.Center
                        ) {
                            Text(
                                text = "TOTAL",
                                style = MaterialTheme.typography.labelSmall,
                                color = Slate400,
                                fontSize = 9.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = String.format("%s%.0f", currencySymbol, totalSpent),
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                        }
                    }

                    // Categories List
                    Column(
                        modifier = Modifier.weight(1f),
                        verticalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        activeCategories.take(5).forEachIndexed { i, cat ->
                            val color = ChartPalette[i % ChartPalette.size]
                            val percent = (cat.spent / totalSpent) * 100.0
                            val isSelected = selectedCategoryId == cat.categoryId

                            Surface(
                                onClick = {
                                    if (isSelected) onSelectCategory(null) else onSelectCategory(cat.categoryId)
                                },
                                shape = RoundedCornerShape(8.dp),
                                color = if (isSelected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f),
                                border = if (isSelected) androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.primary) else null
                            ) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(horizontal = 8.dp, vertical = 5.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Row(
                                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                                        verticalAlignment = Alignment.CenterVertically,
                                        modifier = Modifier.weight(1f)
                                    ) {
                                        Box(
                                            modifier = Modifier
                                                .size(10.dp)
                                                .clip(CircleShape)
                                                .background(color)
                                        )
                                        Text(
                                            text = cat.categoryName,
                                            style = MaterialTheme.typography.bodySmall,
                                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                            maxLines = 1
                                        )
                                    }
                                    Text(
                                        text = String.format("%.0f%%", percent),
                                        style = MaterialTheme.typography.labelSmall,
                                        fontWeight = FontWeight.Bold,
                                        color = color
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun MonthlySpendingTrendChart(
    trendData: List<HistoricalTrendPoint>,
    currencySymbol: String = "$",
    selectedCategoryName: String? = null,
    modifier: Modifier = Modifier
) {
    val density = LocalDensity.current

    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = CardDefaults.outlinedCardBorder(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
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
                    text = if (selectedCategoryName != null) "Trend: $selectedCategoryName" else "6-Month Trend (Spend vs Rollover)",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
            }

            if (trendData.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(140.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text("No historical data available", color = Slate400, style = MaterialTheme.typography.bodyMedium)
                }
            } else {
                val maxSpent = trendData.maxOfOrNull { maxOf(it.spent, it.rollover) } ?: 100.0
                val maxY = (maxOf(maxSpent, 50.0) * 1.2).toFloat()
                val gridColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f)
                val axisColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.35f)
                val textColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)

                val leftPaddingPx = with(density) { 54.dp.toPx() }
                val bottomPaddingPx = with(density) { 30.dp.toPx() }
                val topPaddingPx = with(density) { 16.dp.toPx() }
                val rightPaddingPx = with(density) { 14.dp.toPx() }
                val labelTextSizePx = with(density) { 11.sp.toPx() }

                Canvas(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(190.dp)
                ) {
                    val chartW = size.width - leftPaddingPx - rightPaddingPx
                    val chartH = size.height - bottomPaddingPx - topPaddingPx

                    fun getY(value: Double): Float = topPaddingPx + (chartH - ((value.toFloat() / maxY) * chartH)).coerceIn(0f, chartH)

                    // Y Grid & Numeric Labels
                    val ySteps = 3
                    for (i in 0..ySteps) {
                        val yVal = (maxY / ySteps) * i
                        val yPos = getY(yVal.toDouble())

                        drawLine(
                            color = gridColor,
                            start = Offset(leftPaddingPx, yPos),
                            end = Offset(size.width - rightPaddingPx, yPos),
                            strokeWidth = 1.dp.toPx(),
                            pathEffect = PathEffect.dashPathEffect(floatArrayOf(6f, 6f), 0f)
                        )

                        drawContext.canvas.nativeCanvas.apply {
                            val paint = android.graphics.Paint().apply {
                                color = android.graphics.Color.argb(
                                    (textColor.alpha * 255).toInt(),
                                    (textColor.red * 255).toInt(),
                                    (textColor.green * 255).toInt(),
                                    (textColor.blue * 255).toInt()
                                )
                                textSize = labelTextSizePx
                                textAlign = android.graphics.Paint.Align.RIGHT
                                isAntiAlias = true
                            }
                            drawText(String.format("%s%.0f", currencySymbol, yVal), leftPaddingPx - 10f, yPos + (labelTextSizePx / 3f), paint)
                        }
                    }

                    // Baselines
                    drawLine(
                        color = axisColor,
                        start = Offset(leftPaddingPx, topPaddingPx),
                        end = Offset(leftPaddingPx, size.height - bottomPaddingPx),
                        strokeWidth = 2.dp.toPx()
                    )
                    drawLine(
                        color = axisColor,
                        start = Offset(leftPaddingPx, size.height - bottomPaddingPx),
                        end = Offset(size.width - rightPaddingPx, size.height - bottomPaddingPx),
                        strokeWidth = 2.dp.toPx()
                    )

                    // Bars / Groups for each month
                    val n = trendData.size
                    val slotW = chartW / n
                    val barW = slotW * 0.30f

                    trendData.forEachIndexed { i, pt ->
                        val slotCenter = leftPaddingPx + (i + 0.5f) * slotW

                        // Spent Bar (Red/Orange)
                        val spentH = ((pt.spent.toFloat() / maxY) * chartH).coerceIn(0f, chartH)
                        val spentLeft = slotCenter - barW - 2f
                        drawRoundRect(
                            color = RedDanger,
                            topLeft = Offset(spentLeft, size.height - bottomPaddingPx - spentH),
                            size = Size(barW, spentH),
                            cornerRadius = androidx.compose.ui.geometry.CornerRadius(6f, 6f)
                        )

                        // Rollover Bar (Green) - only when all categories
                        if (selectedCategoryName == null) {
                            val rollH = ((pt.rollover.toFloat() / maxY) * chartH).coerceIn(0f, chartH)
                            val rollLeft = slotCenter + 2f
                            drawRoundRect(
                                color = GreenSuccess,
                                topLeft = Offset(rollLeft, size.height - bottomPaddingPx - rollH),
                                size = Size(barW, rollH),
                                cornerRadius = androidx.compose.ui.geometry.CornerRadius(6f, 6f)
                            )
                        }

                        // X-axis Month Label
                        drawContext.canvas.nativeCanvas.apply {
                            val paint = android.graphics.Paint().apply {
                                color = android.graphics.Color.argb(
                                    (textColor.alpha * 255).toInt(),
                                    (textColor.red * 255).toInt(),
                                    (textColor.green * 255).toInt(),
                                    (textColor.blue * 255).toInt()
                                )
                                textSize = labelTextSizePx
                                textAlign = android.graphics.Paint.Align.CENTER
                                isAntiAlias = true
                            }
                            val shortMonth = if (pt.month.length >= 7) pt.month.substring(5, 7) else pt.month
                            drawText(shortMonth, slotCenter, size.height - bottomPaddingPx + labelTextSizePx + 8f, paint)
                        }
                    }
                }

                // Legend
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    LegendIndicator(color = RedDanger, label = if (selectedCategoryName != null) "$selectedCategoryName Spent" else "Total Spent")
                    if (selectedCategoryName == null) {
                        LegendIndicator(color = GreenSuccess, label = "Rolled to Savings")
                    }
                }
            }
        }
    }
}

@Composable
private fun LegendIndicator(color: Color, label: String) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Box(
            modifier = Modifier
                .size(10.dp)
                .background(color, RoundedCornerShape(2.dp))
        )
        Text(text = label, style = MaterialTheme.typography.labelSmall)
    }
}
