package com.budgetapp.ui.settings

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.budgetapp.data.local.entity.CategoryEntity
import com.budgetapp.data.local.entity.RecurringTransactionEntity
import java.time.LocalDate

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RecurringRuleDialog(
    rule: RecurringTransactionEntity?,
    categories: List<CategoryEntity>,
    currencySymbol: String = "$",
    onDismiss: () -> Unit,
    onSave: (RecurringTransactionEntity) -> Unit
) {
    var description by remember { mutableStateOf(rule?.description ?: "") }
    var amountText by remember { mutableStateOf(rule?.amount?.toString() ?: "") }
    var type by remember { mutableStateOf(rule?.type ?: "expense") }
    var selectedCategoryId by remember { mutableStateOf(rule?.categoryId ?: categories.firstOrNull()?.id) }
    var frequency by remember { mutableStateOf(rule?.frequency ?: "monthly") }
    var nextDueDate by remember { mutableStateOf(rule?.nextDueDate ?: LocalDate.now().toString()) }

    var categoryExpanded by remember { mutableStateOf(false) }
    var freqExpanded by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(if (rule == null) "New Recurring Rule" else "Edit Recurring Rule", fontWeight = FontWeight.Bold)
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                // Type selector
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    FilterChip(
                        selected = type == "expense",
                        onClick = { type = "expense" },
                        label = { Text("Expense") },
                        modifier = Modifier.weight(1f)
                    )
                    FilterChip(
                        selected = type == "income",
                        onClick = { type = "income" },
                        label = { Text("Income") },
                        modifier = Modifier.weight(1f)
                    )
                }

                // Description
                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    label = { Text("Description (e.g. Rent, Netflix)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                // Amount
                OutlinedTextField(
                    value = amountText,
                    onValueChange = { amountText = it },
                    label = { Text("Amount ($currencySymbol)") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                // Category (for expense)
                if (type == "expense" && categories.isNotEmpty()) {
                    ExposedDropdownMenuBox(
                        expanded = categoryExpanded,
                        onExpandedChange = { categoryExpanded = !categoryExpanded }
                    ) {
                        val currentName = categories.find { it.id == selectedCategoryId }?.name ?: "Select Category"
                        OutlinedTextField(
                            value = currentName,
                            onValueChange = {},
                            readOnly = true,
                            label = { Text("Category") },
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = categoryExpanded) },
                            modifier = Modifier.fillMaxWidth().menuAnchor()
                        )
                        ExposedDropdownMenu(
                            expanded = categoryExpanded,
                            onDismissRequest = { categoryExpanded = false }
                        ) {
                            categories.forEach { cat ->
                                DropdownMenuItem(
                                    text = { Text(cat.name) },
                                    onClick = {
                                        selectedCategoryId = cat.id
                                        categoryExpanded = false
                                    }
                                )
                            }
                        }
                    }
                }

                // Frequency Dropdown
                ExposedDropdownMenuBox(
                    expanded = freqExpanded,
                    onExpandedChange = { freqExpanded = !freqExpanded }
                ) {
                    OutlinedTextField(
                        value = frequency.replaceFirstChar { it.uppercase() },
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Frequency") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = freqExpanded) },
                        modifier = Modifier.fillMaxWidth().menuAnchor()
                    )
                    ExposedDropdownMenu(
                        expanded = freqExpanded,
                        onDismissRequest = { freqExpanded = false }
                    ) {
                        listOf("daily", "monthly", "yearly").forEach { f ->
                            DropdownMenuItem(
                                text = { Text(f.replaceFirstChar { it.uppercase() }) },
                                onClick = {
                                    frequency = f
                                    freqExpanded = false
                                }
                            )
                        }
                    }
                }

                // Next Due Date
                OutlinedTextField(
                    value = nextDueDate,
                    onValueChange = { nextDueDate = it },
                    label = { Text("Next Due Date (YYYY-MM-DD)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val amt = amountText.toDoubleOrNull() ?: 0.0
                    if (amt > 0 && description.isNotBlank()) {
                        val newRule = (rule ?: RecurringTransactionEntity(
                            categoryId = if (type == "expense") selectedCategoryId else null,
                            amount = amt,
                            description = description.trim(),
                            type = type,
                            frequency = frequency,
                            nextDueDate = nextDueDate,
                            createdAt = LocalDate.now().toString()
                        )).copy(
                            amount = amt,
                            description = description.trim(),
                            type = type,
                            categoryId = if (type == "expense") selectedCategoryId else null,
                            frequency = frequency,
                            nextDueDate = nextDueDate
                        )
                        onSave(newRule)
                    }
                }
            ) {
                Text("Save Rule")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}
