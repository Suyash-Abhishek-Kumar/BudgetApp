package com.budgetapp.ui.transactions

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CalendarToday
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.budgetapp.data.local.entity.CategoryEntity
import com.budgetapp.data.local.entity.TransactionEntity
import com.budgetapp.ui.theme.RedDanger
import java.time.LocalDate

data class SplitItem(
    val categoryId: Long,
    val amount: String
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddTransactionDialog(
    categories: List<CategoryEntity>,
    onDismiss: () -> Unit,
    onSaveSingle: (TransactionEntity) -> Unit,
    onSaveSplit: (date: String, description: String, splits: List<Pair<Long, Double>>, fundingSource: String) -> Unit
) {
    var amountText by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var transactionType by remember { mutableStateOf("expense") }
    var selectedCategoryId by remember { mutableStateOf<Long?>(categories.firstOrNull()?.id) }
    var fundingSource by remember { mutableStateOf("regular") }
    var txnDate by remember { mutableStateOf(LocalDate.now().toString()) }
    var isSplitEnabled by remember { mutableStateOf(false) }

    // Split rows state
    val splitItems = remember {
        mutableStateListOf(
            SplitItem(categories.firstOrNull()?.id ?: 1L, ""),
            SplitItem(categories.getOrNull(1)?.id ?: categories.firstOrNull()?.id ?: 1L, "")
        )
    }

    var categoryDropdownExpanded by remember { mutableStateOf(false) }
    var showDatePicker by remember { mutableStateOf(false) }

    val totalAmount = amountText.toDoubleOrNull() ?: 0.0
    val allocatedSplitTotal = splitItems.sumOf { it.amount.toDoubleOrNull() ?: 0.0 }
    val unallocatedBalance = totalAmount - allocatedSplitTotal

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(text = "Add Transaction", fontWeight = FontWeight.Bold)
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Type selector
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    FilterChip(
                        selected = transactionType == "expense",
                        onClick = {
                            transactionType = "expense"
                        },
                        label = { Text("Expense") },
                        modifier = Modifier.weight(1f)
                    )
                    FilterChip(
                        selected = transactionType == "income",
                        onClick = {
                            transactionType = "income"
                            isSplitEnabled = false
                        },
                        label = { Text("Income") },
                        modifier = Modifier.weight(1f)
                    )
                }

                // Total Amount
                OutlinedTextField(
                    value = amountText,
                    onValueChange = { amountText = it },
                    label = { Text("Total Amount") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                // Date Picker field
                OutlinedTextField(
                    value = txnDate,
                    onValueChange = { txnDate = it },
                    label = { Text("Date (YYYY-MM-DD)") },
                    trailingIcon = {
                        IconButton(onClick = { showDatePicker = true }) {
                            Icon(Icons.Default.CalendarToday, contentDescription = "Pick Date")
                        }
                    },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                // Description
                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    label = { Text("Description") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                // Split across categories toggle (only for expense)
                if (transactionType == "expense") {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Split across categories", style = MaterialTheme.typography.bodyMedium)
                        Switch(
                            checked = isSplitEnabled,
                            onCheckedChange = { isSplitEnabled = it }
                        )
                    }
                }

                // Category / Source Dropdown
                if (!isSplitEnabled) {
                    val isIncome = transactionType == "income"
                    ExposedDropdownMenuBox(
                        expanded = categoryDropdownExpanded,
                        onExpandedChange = { categoryDropdownExpanded = !categoryDropdownExpanded }
                    ) {
                        val currentCategoryName = if (isIncome) {
                            if (selectedCategoryId == null) "General Income" else categories.find { it.id == selectedCategoryId }?.name ?: "General Income"
                        } else {
                            categories.find { it.id == selectedCategoryId }?.name ?: "Select Category"
                        }

                        OutlinedTextField(
                            value = currentCategoryName,
                            onValueChange = {},
                            readOnly = true,
                            label = { Text(if (isIncome) "Income Source" else "Category") },
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = categoryDropdownExpanded) },
                            modifier = Modifier
                                .fillMaxWidth()
                                .menuAnchor()
                        )
                        ExposedDropdownMenu(
                            expanded = categoryDropdownExpanded,
                            onDismissRequest = { categoryDropdownExpanded = false }
                        ) {
                            if (isIncome) {
                                DropdownMenuItem(
                                    text = { Text("General Income") },
                                    onClick = {
                                        selectedCategoryId = null
                                        categoryDropdownExpanded = false
                                    }
                                )
                                categories.forEach { cat ->
                                    DropdownMenuItem(
                                        text = { Text(cat.name) },
                                        onClick = {
                                            selectedCategoryId = cat.id
                                            categoryDropdownExpanded = false
                                        }
                                    )
                                }
                            } else {
                                categories.forEach { cat ->
                                    DropdownMenuItem(
                                        text = { Text(cat.name) },
                                        onClick = {
                                            selectedCategoryId = cat.id
                                            categoryDropdownExpanded = false
                                        }
                                    )
                                }
                            }
                        }
                    }
                }


                // Dynamic Split Rows Builder
                if (transactionType == "expense" && isSplitEnabled) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
                    ) {
                        Column(
                            modifier = Modifier.padding(12.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text("Itemized Splits", fontWeight = FontWeight.SemiBold)
                                Text(
                                    text = String.format("Remaining: $%.2f", unallocatedBalance),
                                    style = MaterialTheme.typography.labelSmall,
                                    color = if (kotlin.math.abs(unallocatedBalance) < 0.01) MaterialTheme.colorScheme.primary else RedDanger
                                )
                            }

                            splitItems.forEachIndexed { index, split ->
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    var itemDropdownExpanded by remember { mutableStateOf(false) }
                                    Box(modifier = Modifier.weight(1.3f)) {
                                        val catName = categories.find { it.id == split.categoryId }?.name ?: "Category"
                                        OutlinedButton(
                                            onClick = { itemDropdownExpanded = true },
                                            modifier = Modifier.fillMaxWidth(),
                                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp)
                                        ) {
                                            Text(catName, maxLines = 1)
                                        }
                                        DropdownMenu(
                                            expanded = itemDropdownExpanded,
                                            onDismissRequest = { itemDropdownExpanded = false }
                                        ) {
                                            categories.forEach { cat ->
                                                DropdownMenuItem(
                                                    text = { Text(cat.name) },
                                                    onClick = {
                                                        splitItems[index] = split.copy(categoryId = cat.id)
                                                        itemDropdownExpanded = false
                                                    }
                                                )
                                            }
                                        }
                                    }

                                    OutlinedTextField(
                                        value = split.amount,
                                        onValueChange = { newAmt ->
                                            splitItems[index] = split.copy(amount = newAmt)
                                        },
                                        placeholder = { Text("0.00") },
                                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                                        singleLine = true,
                                        modifier = Modifier.weight(1f)
                                    )

                                    if (splitItems.size > 2) {
                                        IconButton(onClick = { splitItems.removeAt(index) }) {
                                            Icon(Icons.Default.Delete, contentDescription = "Remove Split", tint = RedDanger)
                                        }
                                    }
                                }
                            }

                            TextButton(
                                onClick = {
                                    splitItems.add(SplitItem(categories.firstOrNull()?.id ?: 1L, ""))
                                },
                                modifier = Modifier.align(Alignment.Start)
                            ) {
                                Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Add Category Row")
                            }
                        }
                    }
                }

                // Funding Source
                if (transactionType == "expense") {
                    Text(text = "Funding Source", style = MaterialTheme.typography.labelMedium)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        listOf("regular" to "Regular", "savings" to "Savings", "emergency_fund" to "Emergency").forEach { (key, label) ->
                            FilterChip(
                                selected = fundingSource == key,
                                onClick = { fundingSource = key },
                                label = { Text(label, style = MaterialTheme.typography.labelSmall) }
                            )
                        }
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (totalAmount > 0) {
                        if (isSplitEnabled) {
                            val validSplits = splitItems.mapNotNull {
                                val amt = it.amount.toDoubleOrNull()
                                if (amt != null && amt > 0) Pair(it.categoryId, amt) else null
                            }
                            if (validSplits.isNotEmpty() && kotlin.math.abs(unallocatedBalance) < 0.05) {
                                onSaveSplit(txnDate, description, validSplits, fundingSource)
                            }
                        } else {
                            val newTx = TransactionEntity(
                                date = txnDate,
                                amount = totalAmount,
                                type = transactionType,
                                categoryId = selectedCategoryId,
                                description = description,
                                fundingSource = if (transactionType == "income") "regular" else fundingSource,
                                status = "confirmed"
                            )
                            onSaveSingle(newTx)
                        }
                    }
                }
            ) {
                Text("Save")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )

    if (showDatePicker) {
        val datePickerState = rememberDatePickerState(
            initialSelectedDateMillis = System.currentTimeMillis()
        )
        DatePickerDialog(
            onDismissRequest = { showDatePicker = false },
            confirmButton = {
                TextButton(onClick = {
                    datePickerState.selectedDateMillis?.let { millis ->
                        txnDate = java.time.Instant.ofEpochMilli(millis)
                            .atZone(java.time.ZoneId.systemDefault())
                            .toLocalDate()
                            .toString()
                    }
                    showDatePicker = false
                }) {
                    Text("OK")
                }
            },
            dismissButton = {
                TextButton(onClick = { showDatePicker = false }) {
                    Text("Cancel")
                }
            }
        ) {
            DatePicker(state = datePickerState)
        }
    }
}
