package com.budgetapp.ui.dashboard

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.budgetapp.data.local.entity.CategoryEntity

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CategoryReallocationDialog(
    categories: List<CategoryEntity>,
    onDismiss: () -> Unit,
    onTransfer: (fromCatId: Long, toCatId: Long, amount: Double) -> Unit
) {
    if (categories.size < 2) return

    var fromCatId by remember { mutableStateOf(categories[0].id) }
    var toCatId by remember { mutableStateOf(categories[1].id) }
    var amountText by remember { mutableStateOf("") }

    var fromExpanded by remember { mutableStateOf(false) }
    var toExpanded by remember { mutableStateOf(false) }

    val fromCat = categories.find { it.id == fromCatId } ?: categories[0]
    val toCat = categories.find { it.id == toCatId } ?: categories[1]
    val amount = amountText.toDoubleOrNull() ?: 0.0

    val isValid = amount > 0 && amount <= fromCat.hardLimit && fromCatId != toCatId

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text("🔄 Reallocate Envelope Budget", fontWeight = FontWeight.Bold)
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    text = "Move budget limit between categories without modifying your income or savings.",
                    style = MaterialTheme.typography.bodySmall
                )

                // From Category
                ExposedDropdownMenuBox(
                    expanded = fromExpanded,
                    onExpandedChange = { fromExpanded = !fromExpanded }
                ) {
                    OutlinedTextField(
                        value = "${fromCat.name} (Limit: $${fromCat.hardLimit.toInt()})",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("From Category") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = fromExpanded) },
                        modifier = Modifier.fillMaxWidth().menuAnchor()
                    )
                    ExposedDropdownMenu(
                        expanded = fromExpanded,
                        onDismissRequest = { fromExpanded = false }
                    ) {
                        categories.forEach { cat ->
                            DropdownMenuItem(
                                text = { Text("${cat.name} (Limit: $${cat.hardLimit.toInt()})") },
                                onClick = {
                                    fromCatId = cat.id
                                    fromExpanded = false
                                }
                            )
                        }
                    }
                }

                // To Category
                ExposedDropdownMenuBox(
                    expanded = toExpanded,
                    onExpandedChange = { toExpanded = !toExpanded }
                ) {
                    OutlinedTextField(
                        value = "${toCat.name} (Limit: $${toCat.hardLimit.toInt()})",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("To Category") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = toExpanded) },
                        modifier = Modifier.fillMaxWidth().menuAnchor()
                    )
                    ExposedDropdownMenu(
                        expanded = toExpanded,
                        onDismissRequest = { toExpanded = false }
                    ) {
                        categories.forEach { cat ->
                            DropdownMenuItem(
                                text = { Text("${cat.name} (Limit: $${cat.hardLimit.toInt()})") },
                                onClick = {
                                    toCatId = cat.id
                                    toExpanded = false
                                }
                            )
                        }
                    }
                }

                // Transfer Amount
                OutlinedTextField(
                    value = amountText,
                    onValueChange = { amountText = it },
                    label = { Text("Transfer Amount") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    isError = amount > fromCat.hardLimit
                )

                if (isValid) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
                    ) {
                        Column(modifier = Modifier.padding(10.dp)) {
                            Text("New Limits Preview:", fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.labelSmall)
                            Text(
                                "• ${fromCat.name}: $${(fromCat.hardLimit - amount).toInt()} (was $${fromCat.hardLimit.toInt()})",
                                style = MaterialTheme.typography.labelSmall
                            )
                            Text(
                                "• ${toCat.name}: $${(toCat.hardLimit + amount).toInt()} (was $${toCat.hardLimit.toInt()})",
                                style = MaterialTheme.typography.labelSmall
                            )
                        }
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (isValid) {
                        onTransfer(fromCatId, toCatId, amount)
                    }
                },
                enabled = isValid
            ) {
                Text("Confirm Transfer")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}
