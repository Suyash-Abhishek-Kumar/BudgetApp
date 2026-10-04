package com.budgetapp.ui.transactions

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.UploadFile
import androidx.compose.material.icons.filled.FileDownload
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.budgetapp.data.local.entity.CategoryEntity
import com.budgetapp.data.local.entity.TransactionEntity
import com.budgetapp.ui.theme.GreenContainer
import com.budgetapp.ui.theme.GreenSuccess
import com.budgetapp.ui.theme.RedContainer
import com.budgetapp.ui.theme.RedDanger
import com.budgetapp.ui.theme.Slate400
import java.time.LocalDate

@Composable
fun TransactionListScreen(
    transactions: List<TransactionEntity>,
    pendingTransactions: List<TransactionEntity>,
    categories: List<CategoryEntity>,
    currencySymbol: String = "$",
    isPrivacyMode: Boolean = false,
    onApprovePending: (Long) -> Unit,
    onDeleteTransaction: (TransactionEntity) -> Unit,
    onEditTransaction: (TransactionEntity) -> Unit,
    onExportCsv: () -> Unit,
    onImportCsv: () -> Unit,
    modifier: Modifier = Modifier
) {
    var searchQuery by remember { mutableStateOf("") }
    var selectedFilter by remember { mutableStateOf("All") } // "All", "This Month", "Last 30 Days", "Expenses", "Income"
    val catMap = remember(categories) { categories.associateBy { it.id } }

    val currentMonth = remember { LocalDate.now().toString().substring(0, 7) }
    val thirtyDaysAgo = remember { LocalDate.now().minusDays(30).toString() }

    // Filter transactions
    val filteredTransactions = remember(transactions, searchQuery, selectedFilter) {
        transactions.filter { tx ->
            val matchesQuery = searchQuery.isBlank() ||
                    (tx.description ?: "").contains(searchQuery, ignoreCase = true) ||
                    (catMap[tx.categoryId]?.name ?: "").contains(searchQuery, ignoreCase = true)

            val matchesFilter = when (selectedFilter) {
                "This Month" -> tx.date.startsWith(currentMonth)
                "Last 30 Days" -> tx.date >= thirtyDaysAgo
                "Expenses" -> tx.type == "expense"
                "Income" -> tx.type == "income"
                else -> true
            }

            matchesQuery && matchesFilter
        }
    }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Top Toolbar: Search & Action buttons
        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    OutlinedTextField(
                        value = searchQuery,
                        onValueChange = { searchQuery = it },
                        placeholder = { Text("Search transactions...") },
                        leadingIcon = { Icon(Icons.Default.Search, contentDescription = "Search") },
                        trailingIcon = {
                            if (searchQuery.isNotEmpty()) {
                                IconButton(onClick = { searchQuery = "" }) {
                                    Icon(Icons.Default.Close, contentDescription = "Clear")
                                }
                            }
                        },
                        singleLine = true,
                        modifier = Modifier.weight(1f)
                    )

                    IconButton(onClick = onImportCsv) {
                        Icon(Icons.Default.UploadFile, contentDescription = "Import CSV", tint = MaterialTheme.colorScheme.primary)
                    }

                    IconButton(onClick = onExportCsv) {
                        Icon(Icons.Default.FileDownload, contentDescription = "Export CSV", tint = MaterialTheme.colorScheme.primary)
                    }
                }

                // Filter chips row
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    val filterOptions = listOf("All", "This Month", "Last 30 Days", "Expenses", "Income")
                    items(filterOptions) { filter ->
                        FilterChip(
                            selected = selectedFilter == filter,
                            onClick = { selectedFilter = filter },
                            label = { Text(filter) }
                        )
                    }
                }
            }
        }

        // Pending Recurring Approvals Section
        if (pendingTransactions.isNotEmpty()) {
            item {
                Text(
                    text = "Pending Recurring Approvals (${pendingTransactions.size})",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            items(pendingTransactions) { tx ->
                PendingTransactionItem(
                    tx = tx,
                    currency = currencySymbol,
                    onApprove = { onApprovePending(tx.id) },
                    onDelete = { onDeleteTransaction(tx) }
                )
            }

            item {
                HorizontalDivider(modifier = Modifier.padding(vertical = 4.dp))
            }
        }

        // Transactions Header
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Ledger (${filteredTransactions.size})",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold
                )
            }
        }

        if (filteredTransactions.isEmpty()) {
            item {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(32.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(text = "No matching transactions", color = Slate400)
                }
            }
        } else {
            items(filteredTransactions, key = { it.id }) { tx ->
                val categoryName = catMap[tx.categoryId]?.name ?: if (tx.type == "income") "General Income" else "Uncategorized"
                TransactionRow(
                    tx = tx,
                    categoryName = categoryName,
                    currency = currencySymbol,
                    isPrivacy = isPrivacyMode,
                    onEdit = { onEditTransaction(tx) },
                    onDelete = { onDeleteTransaction(tx) }
                )
            }
        }
    }
}

@Composable
fun TransactionRow(
    tx: TransactionEntity,
    categoryName: String,
    currency: String,
    isPrivacy: Boolean,
    onEdit: () -> Unit,
    onDelete: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onEdit),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = CardDefaults.outlinedCardBorder()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = tx.description?.ifBlank { categoryName } ?: categoryName,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = "${tx.date} • $categoryName • ${tx.fundingSource}${if (tx.splitGroupId != null) " (Split)" else ""}",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.55f)
                )
            }

            val isIncome = tx.type == "income"
            val displayAmount = if (isPrivacy) "••••" else String.format(
                "%s%s%.2f",
                if (isIncome) "+" else "-",
                currency,
                tx.amount
            )

            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = if (isIncome) GreenContainer.copy(alpha = 0.5f) else RedContainer.copy(alpha = 0.4f),
                    modifier = Modifier.padding(end = 6.dp)
                ) {
                    Text(
                        text = displayAmount,
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold,
                        color = if (isIncome) GreenSuccess else RedDanger,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
                IconButton(onClick = onEdit) {
                    Icon(
                        imageVector = Icons.Default.Edit,
                        contentDescription = "Edit",
                        tint = Slate400,
                        modifier = Modifier.size(18.dp)
                    )
                }
                IconButton(onClick = onDelete) {
                    Icon(
                        imageVector = Icons.Default.Delete,
                        contentDescription = "Delete",
                        tint = RedDanger.copy(alpha = 0.7f),
                        modifier = Modifier.size(18.dp)
                    )
                }
            }
        }
    }
}

@Composable
fun PendingTransactionItem(
    tx: TransactionEntity,
    currency: String,
    onApprove: () -> Unit,
    onDelete: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.3f)
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = tx.description ?: "Recurring Item",
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "Due: ${tx.date} • Amount: $currency${tx.amount}",
                    style = MaterialTheme.typography.bodySmall
                )
            }
            Row {
                IconButton(onClick = onApprove) {
                    Icon(
                        imageVector = Icons.Default.Check,
                        contentDescription = "Approve",
                        tint = GreenSuccess
                    )
                }
                IconButton(onClick = onDelete) {
                    Icon(
                        imageVector = Icons.Default.Delete,
                        contentDescription = "Reject",
                        tint = RedDanger
                    )
                }
            }
        }
    }
}
