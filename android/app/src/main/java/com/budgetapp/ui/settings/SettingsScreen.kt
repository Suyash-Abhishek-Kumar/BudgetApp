package com.budgetapp.ui.settings

import android.content.Context
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Key
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.RestartAlt
import androidx.compose.material.icons.filled.Save
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import com.budgetapp.domain.ai.GeminiAssistant
import com.budgetapp.data.local.entity.CategoryEntity
import com.budgetapp.data.local.entity.EmergencyFundEntity
import com.budgetapp.data.local.entity.EmergencyFundLogEntity
import com.budgetapp.data.local.entity.RecurringTransactionEntity
import com.budgetapp.domain.backup.BackupFileInfo
import com.budgetapp.domain.backup.DatabaseBackupManager
import com.budgetapp.ui.theme.GreenSuccess
import com.budgetapp.ui.theme.PrimaryBlue
import com.budgetapp.ui.theme.PurpleAccent
import com.budgetapp.ui.theme.RedDanger
import com.budgetapp.ui.theme.Slate400

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    categories: List<CategoryEntity>,
    emergencyFund: EmergencyFundEntity?,
    emergencyLogs: List<EmergencyFundLogEntity>,
    recurringList: List<RecurringTransactionEntity>,
    currencySymbol: String,
    isPrivacyMode: Boolean,
    onUpdateCurrency: (String) -> Unit,
    onTogglePrivacy: (Boolean) -> Unit,
    onAddCategory: (name: String, softLimit: Double, hardLimit: Double) -> Unit,
    onEditCategory: (CategoryEntity) -> Unit,
    onDeleteCategory: (CategoryEntity) -> Unit,
    onDepositEmergencyFund: (Double, String?) -> Unit,
    onWithdrawEmergencyFund: (Double, String?) -> Unit,
    onSaveRecurringRule: (RecurringTransactionEntity) -> Unit,
    onDeleteRecurring: (RecurringTransactionEntity) -> Unit,
    onManualRollover: () -> Unit,
    archivesList: List<com.budgetapp.domain.model.MonthArchiveRecord> = emptyList(),
    onViewArchiveInDashboard: (String) -> Unit = {},
    geminiApiKey: String = "",
    geminiModel: String = "gemini-1.5-flash",
    onSaveAiConfig: (apiKey: String, model: String) -> Unit = { _, _ -> },
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    var selectedTab by remember { mutableIntStateOf(0) }
    val tabTitles = listOf("General", "Categories", "Emergency Fund", "Recurring", "Archives", "AI Assistant", "Backups")

    var showAddCategoryDialog by remember { mutableStateOf(false) }
    var categoryToEdit by remember { mutableStateOf<CategoryEntity?>(null) }
    var showEfTransferDialog by remember { mutableStateOf<String?>(null) }
    var showRecurringRuleDialog by remember { mutableStateOf<RecurringTransactionEntity?>(null) }

    // Backups list state
    var backupList by remember { mutableStateOf(DatabaseBackupManager.listBackups(context)) }

    Column(modifier = modifier.fillMaxSize()) {
        ScrollableTabRow(
            selectedTabIndex = selectedTab,
            edgePadding = 16.dp,
            divider = { HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant) }
        ) {
            tabTitles.forEachIndexed { index, title ->
                Tab(
                    selected = selectedTab == index,
                    onClick = { selectedTab = index },
                    text = {
                        Text(
                            text = title,
                            maxLines = 1,
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = if (selectedTab == index) FontWeight.Bold else FontWeight.Normal
                        )
                    }
                )
            }
        }

        Box(modifier = Modifier.fillMaxSize().padding(16.dp)) {
            when (selectedTab) {
                0 -> GeneralSettingsTab(
                    currencySymbol = currencySymbol,
                    isPrivacyMode = isPrivacyMode,
                    onUpdateCurrency = onUpdateCurrency,
                    onTogglePrivacy = onTogglePrivacy,
                    onManualRollover = onManualRollover
                )
                1 -> CategoriesSettingsTab(
                    categories = categories,
                    currencySymbol = currencySymbol,
                    onAdd = { showAddCategoryDialog = true },
                    onEdit = { categoryToEdit = it },
                    onDelete = onDeleteCategory
                )
                2 -> EmergencyFundSettingsTab(
                    emergencyFund = emergencyFund,
                    logs = emergencyLogs,
                    currencySymbol = currencySymbol,
                    onDeposit = { showEfTransferDialog = "deposit" },
                    onWithdraw = { showEfTransferDialog = "withdraw" }
                )
                3 -> RecurringSettingsTab(
                    recurringList = recurringList,
                    categories = categories,
                    currencySymbol = currencySymbol,
                    onAddRule = {
                        showRecurringRuleDialog = RecurringTransactionEntity(
                            amount = 0.0,
                            type = "expense",
                            frequency = "monthly",
                            nextDueDate = java.time.LocalDate.now().toString(),
                            createdAt = java.time.LocalDate.now().toString()
                        )
                    },
                    onEditRule = { showRecurringRuleDialog = it },
                    onDelete = onDeleteRecurring
                )
                4 -> ArchivesSettingsTab(
                    archives = archivesList,
                    currencySymbol = currencySymbol,
                    onViewInDashboard = onViewArchiveInDashboard
                )
                5 -> AiAssistantSettingsTab(
                    initialApiKey = geminiApiKey,
                    initialModel = geminiModel,
                    onSave = onSaveAiConfig
                )
                6 -> BackupsTab(
                    backups = backupList,
                    onCreateBackup = {
                        try {
                            DatabaseBackupManager.createBackup(context)
                            backupList = DatabaseBackupManager.listBackups(context)
                        } catch (e: Exception) {
                            // Ignored or toast
                        }
                    },
                    onRestoreBackup = { backupFile ->
                        try {
                            DatabaseBackupManager.restoreBackup(context, backupFile.file)
                        } catch (e: Exception) {
                            // Ignored or toast
                        }
                    },
                    onDeleteBackup = { backupFile ->
                        DatabaseBackupManager.deleteBackup(backupFile.file)
                        backupList = DatabaseBackupManager.listBackups(context)
                    }
                )
            }
        }
    }


    if (showAddCategoryDialog) {
        CategoryFormDialog(
            category = null,
            currencySymbol = currencySymbol,
            onDismiss = { showAddCategoryDialog = false },
            onSave = { name, soft, hard ->
                onAddCategory(name, soft, hard)
                showAddCategoryDialog = false
            }
        )
    }

    categoryToEdit?.let { cat ->
        CategoryFormDialog(
            category = cat,
            currencySymbol = currencySymbol,
            onDismiss = { categoryToEdit = null },
            onSave = { name, soft, hard ->
                onEditCategory(cat.copy(name = name, softLimit = soft, hardLimit = hard))
                categoryToEdit = null
            }
        )
    }

    showEfTransferDialog?.let { mode ->
        EfTransferDialog(
            mode = mode,
            currencySymbol = currencySymbol,
            currentBalance = emergencyFund?.balance ?: 0.0,
            onDismiss = { showEfTransferDialog = null },
            onConfirm = { amt, note ->
                if (mode == "deposit") {
                    onDepositEmergencyFund(amt, note)
                } else {
                    onWithdrawEmergencyFund(amt, note)
                }
                showEfTransferDialog = null
            }
        )
    }

    showRecurringRuleDialog?.let { ruleToEdit ->
        RecurringRuleDialog(
            rule = if (ruleToEdit.id == 0L) null else ruleToEdit,
            categories = categories,
            currencySymbol = currencySymbol,
            onDismiss = { showRecurringRuleDialog = null },
            onSave = { savedRule ->
                onSaveRecurringRule(savedRule)
                showRecurringRuleDialog = null
            }
        )
    }
}

@Composable
fun GeneralSettingsTab(
    currencySymbol: String,
    isPrivacyMode: Boolean,
    onUpdateCurrency: (String) -> Unit,
    onTogglePrivacy: (Boolean) -> Unit,
    onManualRollover: () -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text("Preferences", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)

        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text("Privacy Mode", fontWeight = FontWeight.SemiBold)
                        Text("Mask financial figures with bullets", style = MaterialTheme.typography.bodySmall, color = Slate400)
                    }
                    Switch(checked = isPrivacyMode, onCheckedChange = onTogglePrivacy)
                }

                HorizontalDivider()

                Text("Currency Symbol", fontWeight = FontWeight.SemiBold)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("$", "₹", "€", "£", "¥").forEach { sym ->
                        FilterChip(
                            selected = currencySymbol == sym,
                            onClick = { onUpdateCurrency(sym) },
                            label = { Text(sym, fontWeight = FontWeight.Bold) }
                        )
                    }
                }
            }
        }

        // Rollover Engine Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Month-End Rollover Engine", fontWeight = FontWeight.SemiBold)
                Text(
                    "Process surplus closeout from past unclosed months and allocate to savings and emergency fund.",
                    style = MaterialTheme.typography.bodySmall,
                    color = Slate400
                )
                Button(onClick = onManualRollover, modifier = Modifier.padding(top = 4.dp)) {
                    Icon(Icons.Default.RestartAlt, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Trigger Rollover Check")
                }
            }
        }
    }
}

@Composable
fun BackupsTab(
    backups: List<BackupFileInfo>,
    onCreateBackup: () -> Unit,
    onRestoreBackup: (BackupFileInfo) -> Unit,
    onDeleteBackup: (BackupFileInfo) -> Unit
) {
    LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Database Snapshots", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Button(onClick = onCreateBackup) {
                    Icon(Icons.Default.Save, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Create Snapshot")
                }
            }
        }

        if (backups.isEmpty()) {
            item {
                Text("No database snapshots found yet. Tap 'Create Snapshot' to save a backup.", color = Slate400)
            }
        } else {
            items(backups, key = { it.filename }) { b ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(b.filename, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodyMedium)
                            Text("${b.createdAt} • ${b.sizeKb} KB", style = MaterialTheme.typography.labelSmall, color = Slate400)
                        }
                        Row {
                            TextButton(onClick = { onRestoreBackup(b) }) {
                                Text("Restore")
                            }
                            IconButton(onClick = { onDeleteBackup(b) }) {
                                Icon(Icons.Default.Delete, contentDescription = "Delete", tint = RedDanger)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun ArchivesSettingsTab(
    archives: List<com.budgetapp.domain.model.MonthArchiveRecord>,
    currencySymbol: String,
    onViewInDashboard: (String) -> Unit
) {
    LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("Closed Month Archives", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text(
                    "Historical ledgers and finalized values of all past closed months.",
                    style = MaterialTheme.typography.bodySmall,
                    color = Slate400
                )
            }
        }

        if (archives.isEmpty()) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth().padding(top = 16.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
                ) {
                    Column(
                        modifier = Modifier.padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text("📁 No closed months recorded yet.", fontWeight = FontWeight.Bold)
                        Text(
                            "When a month concludes and rollover runs, its permanent snapshot will appear here.",
                            style = MaterialTheme.typography.bodySmall,
                            color = Slate400
                        )
                    }
                }
            }
        } else {
            items(archives, key = { it.month }) { arch ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(14.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                Text(
                                    text = "📅 ${arch.month}",
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.Bold
                                )
                                SuggestionChip(
                                    onClick = {},
                                    label = { Text("CLOSED & ARCHIVED", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold) },
                                    colors = SuggestionChipDefaults.suggestionChipColors(
                                        containerColor = GreenSuccess.copy(alpha = 0.15f),
                                        labelColor = GreenSuccess
                                    ),
                                    border = null
                                )
                            }

                            Button(
                                onClick = { onViewInDashboard(arch.month) },
                                contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                            ) {
                                Text("View in Dashboard ↗", style = MaterialTheme.typography.labelSmall)
                            }
                        }

                        HorizontalDivider(color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f))

                        // Financial Metric Pills 2x2 Responsive Grid
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                ArchiveStatBox(title = "Total Income", value = arch.totalIncome, currency = currencySymbol, color = PrimaryBlue, modifier = Modifier.weight(1f))
                                ArchiveStatBox(title = "Total Spent", value = arch.totalSpent, currency = currencySymbol, color = RedDanger, modifier = Modifier.weight(1f))
                            }
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                ArchiveStatBox(title = "Savings Rollover", value = arch.rolloverSavings, currency = currencySymbol, color = GreenSuccess, modifier = Modifier.weight(1f))
                                ArchiveStatBox(title = "EF Delta", value = arch.rolloverEf, currency = currencySymbol, color = PurpleAccent, modifier = Modifier.weight(1f))
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ArchiveStatBox(
    title: String,
    value: Double,
    currency: String,
    color: Color,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(10.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(2.dp)
        ) {
            Text(title, style = MaterialTheme.typography.labelSmall, color = Slate400, maxLines = 1)
            Text(
                text = String.format("%s%.2f", currency, value),
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Bold,
                color = color,
                maxLines = 1
            )
        }
    }
}


@Composable
fun CategoriesSettingsTab(
    categories: List<CategoryEntity>,
    currencySymbol: String,
    onAdd: () -> Unit,
    onEdit: (CategoryEntity) -> Unit,
    onDelete: (CategoryEntity) -> Unit
) {
    LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Category Limits", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Button(onClick = onAdd) {
                    Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Add")
                }
            }
        }

        items(categories, key = { it.id }) { cat ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(8.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(cat.name, fontWeight = FontWeight.Bold)
                        Text(
                            "Soft: $currencySymbol${cat.softLimit.toInt()} • Hard: $currencySymbol${cat.hardLimit.toInt()}",
                            style = MaterialTheme.typography.bodySmall,
                            color = Slate400
                        )
                    }
                    Row {
                        IconButton(onClick = { onEdit(cat) }) {
                            Icon(Icons.Default.Edit, contentDescription = "Edit", tint = Slate400, modifier = Modifier.size(18.dp))
                        }
                        IconButton(onClick = { onDelete(cat) }) {
                            Icon(Icons.Default.Delete, contentDescription = "Delete", tint = RedDanger, modifier = Modifier.size(18.dp))
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun EmergencyFundSettingsTab(
    emergencyFund: EmergencyFundEntity?,
    logs: List<EmergencyFundLogEntity>,
    currencySymbol: String,
    onDeposit: () -> Unit,
    onWithdraw: () -> Unit
) {
    LazyColumn(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
            ) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Emergency Fund Reserve", style = MaterialTheme.typography.labelMedium)
                    Text(
                        "$currencySymbol${String.format("%.2f", emergencyFund?.balance ?: 0.0)}",
                        style = MaterialTheme.typography.headlineLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.padding(top = 4.dp)) {
                        Button(onClick = onDeposit) { Text("Deposit") }
                        OutlinedButton(onClick = onWithdraw) { Text("Withdraw") }
                    }
                }
            }
        }

        item {
            Text("Transfer Activity Log", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        }

        if (logs.isEmpty()) {
            item {
                Text("No transfers recorded yet.", color = Slate400, style = MaterialTheme.typography.bodySmall)
            }
        } else {
            items(logs, key = { it.id }) { log ->
                val isDeposit = log.amount > 0
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text(log.note?.ifBlank { "Manual Transfer" } ?: "Manual Transfer", fontWeight = FontWeight.SemiBold)
                        Text("${log.date} • ${log.source}", style = MaterialTheme.typography.labelSmall, color = Slate400)
                    }
                    Text(
                        "${if (isDeposit) "+" else ""}$currencySymbol${String.format("%.2f", log.amount)}",
                        color = if (isDeposit) GreenSuccess else RedDanger,
                        fontWeight = FontWeight.Bold
                    )
                }
                HorizontalDivider()
            }
        }
    }
}

@Composable
fun RecurringSettingsTab(
    recurringList: List<RecurringTransactionEntity>,
    categories: List<CategoryEntity>,
    currencySymbol: String,
    onAddRule: () -> Unit,
    onEditRule: (RecurringTransactionEntity) -> Unit,
    onDelete: (RecurringTransactionEntity) -> Unit
) {
    val catMap = remember(categories) { categories.associateBy { it.id } }

    LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Scheduled Rules", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Button(onClick = onAddRule) {
                    Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Add Rule")
                }
            }
        }

        if (recurringList.isEmpty()) {
            item {
                Text("No recurring transaction rules registered.", color = Slate400)
            }
        } else {
            items(recurringList, key = { it.id }) { rule ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(rule.description?.ifBlank { "Recurring" } ?: "Recurring", fontWeight = FontWeight.Bold)
                            Text(
                                "Due: ${rule.nextDueDate} • Every ${rule.frequency} • $currencySymbol${rule.amount}",
                                style = MaterialTheme.typography.bodySmall,
                                color = Slate400
                            )
                        }
                        Row {
                            IconButton(onClick = { onEditRule(rule) }) {
                                Icon(Icons.Default.Edit, contentDescription = "Edit", tint = Slate400)
                            }
                            IconButton(onClick = { onDelete(rule) }) {
                                Icon(Icons.Default.Delete, contentDescription = "Delete", tint = RedDanger)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun CategoryFormDialog(
    category: CategoryEntity?,
    currencySymbol: String,
    onDismiss: () -> Unit,
    onSave: (name: String, softLimit: Double, hardLimit: Double) -> Unit
) {
    var name by remember { mutableStateOf(category?.name ?: "") }
    var softText by remember { mutableStateOf(category?.softLimit?.toInt()?.toString() ?: "100") }
    var hardText by remember { mutableStateOf(category?.hardLimit?.toInt()?.toString() ?: "150") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (category == null) "New Category" else "Edit Category") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Name") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = softText,
                    onValueChange = { softText = it },
                    label = { Text("Soft Limit ($currencySymbol)") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = hardText,
                    onValueChange = { hardText = it },
                    label = { Text("Hard Limit ($currencySymbol)") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val soft = softText.toDoubleOrNull() ?: 0.0
                    val hard = hardText.toDoubleOrNull() ?: 0.0
                    if (name.isNotBlank() && hard >= soft && hard > 0) {
                        onSave(name.trim(), soft, hard)
                    }
                }
            ) {
                Text("Save")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}

@Composable
fun EfTransferDialog(
    mode: String,
    currencySymbol: String,
    currentBalance: Double,
    onDismiss: () -> Unit,
    onConfirm: (amount: Double, note: String?) -> Unit
) {
    var amountText by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (mode == "deposit") "Emergency Fund Deposit" else "Emergency Fund Withdrawal") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(
                    value = amountText,
                    onValueChange = { amountText = it },
                    label = { Text("Amount ($currencySymbol)") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = note,
                    onValueChange = { note = it },
                    label = { Text("Reason / Note (optional)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val amt = amountText.toDoubleOrNull() ?: 0.0
                    if (amt > 0 && (mode == "deposit" || amt <= currentBalance)) {
                        onConfirm(amt, note.ifBlank { null })
                    }
                }
            ) {
                Text("Confirm")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AiAssistantSettingsTab(
    initialApiKey: String,
    initialModel: String,
    onSave: (apiKey: String, model: String) -> Unit
) {
    var apiKeyText by remember(initialApiKey) { mutableStateOf(initialApiKey) }
    var selectedModel by remember(initialModel) { mutableStateOf(initialModel.ifBlank { GeminiAssistant.DEFAULT_MODEL }) }
    var keyVisible by remember { mutableStateOf(false) }
    var isDiscoveringModels by remember { mutableStateOf(false) }
    var availableModels by remember { mutableStateOf(GeminiAssistant.DEFAULT_MODELS) }
    var modelDropdownExpanded by remember { mutableStateOf(false) }
    var statusMessage by remember { mutableStateOf<String?>(null) }
    var isSuccessStatus by remember { mutableStateOf(true) }

    val coroutineScope = rememberCoroutineScope()

    LazyColumn(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        item {
            Text("AI Assistant Configuration", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        }

        // API Key Card
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                border = CardDefaults.outlinedCardBorder()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(Icons.Default.Key, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                        Text("Google Gemini API Key", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    }

                    Text(
                        "Your API key enables the AI Financial Assistant to analyze budgets and answer questions. Stored locally and securely on your device.",
                        style = MaterialTheme.typography.bodySmall,
                        color = Slate400
                    )

                    OutlinedTextField(
                        value = apiKeyText,
                        onValueChange = { apiKeyText = it },
                        placeholder = { Text("AIzaSy...") },
                        visualTransformation = if (keyVisible) VisualTransformation.None else PasswordVisualTransformation(),
                        trailingIcon = {
                            IconButton(onClick = { keyVisible = !keyVisible }) {
                                Icon(
                                    imageVector = if (keyVisible) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                                    contentDescription = if (keyVisible) "Hide key" else "Show key"
                                )
                            }
                        },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp)
                    )

                    if (apiKeyText.isNotBlank()) {
                        Surface(
                            color = GreenSuccess.copy(alpha = 0.12f),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                Icon(Icons.Default.Check, contentDescription = null, tint = GreenSuccess, modifier = Modifier.size(16.dp))
                                Text(
                                    "API key is configured and stored locally.",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = GreenSuccess,
                                    fontWeight = FontWeight.Medium
                                )
                            }
                        }
                    }
                }
            }
        }

        // Model Selection & Discovery Card
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                border = CardDefaults.outlinedCardBorder()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(Icons.Default.AutoAwesome, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                        Text("Model Selection", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    }

                    Text(
                        "Choose which Gemini model powers your assistant. Auto-detect queries Google API to reveal all live models accessible to your API key.",
                        style = MaterialTheme.typography.bodySmall,
                        color = Slate400
                    )

                    // Model Dropdown
                    ExposedDropdownMenuBox(
                        expanded = modelDropdownExpanded,
                        onExpandedChange = { modelDropdownExpanded = !modelDropdownExpanded }
                    ) {
                        OutlinedTextField(
                            value = selectedModel,
                            onValueChange = {},
                            readOnly = true,
                            label = { Text("Active Model") },
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = modelDropdownExpanded) },
                            modifier = Modifier
                                .fillMaxWidth()
                                .menuAnchor(),
                            shape = RoundedCornerShape(12.dp)
                        )
                        ExposedDropdownMenu(
                            expanded = modelDropdownExpanded,
                            onDismissRequest = { modelDropdownExpanded = false }
                        ) {
                            availableModels.forEach { m ->
                                DropdownMenuItem(
                                    text = {
                                        Text(
                                            text = m,
                                            fontWeight = if (m == selectedModel) FontWeight.Bold else FontWeight.Normal
                                        )
                                    },
                                    onClick = {
                                        selectedModel = m
                                        modelDropdownExpanded = false
                                    }
                                )
                            }
                        }
                    }

                    // Auto-Detect Live Models Button
                    OutlinedButton(
                        onClick = {
                            if (apiKeyText.isBlank()) {
                                statusMessage = "Please enter an API key above before detecting models."
                                isSuccessStatus = false
                                return@OutlinedButton
                            }
                            isDiscoveringModels = true
                            statusMessage = "Querying Google Gemini API for active models..."
                            isSuccessStatus = true

                            coroutineScope.launch {
                                val discovered = GeminiAssistant.fetchAvailableModels(apiKeyText.trim())
                                isDiscoveringModels = false
                                if (discovered.isNotEmpty()) {
                                    availableModels = discovered
                                    if (!discovered.contains(selectedModel)) {
                                        selectedModel = discovered.first()
                                    }
                                    statusMessage = "✅ Discovered ${discovered.size} live model(s) available for your API key."
                                    isSuccessStatus = true
                                } else {
                                    statusMessage = "Could not discover models. Kept default model list."
                                    isSuccessStatus = false
                                }
                            }
                        },
                        enabled = !isDiscoveringModels,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        if (isDiscoveringModels) {
                            CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Querying Gemini API...")
                        } else {
                            Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Auto-Detect Available Models")
                        }
                    }

                    // Status Message
                    statusMessage?.let { msg ->
                        Text(
                            text = msg,
                            style = MaterialTheme.typography.bodySmall,
                            color = if (isSuccessStatus) GreenSuccess else RedDanger,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
            }
        }

        // Save AI Configuration Button
        item {
            Button(
                onClick = {
                    onSave(apiKeyText.trim(), selectedModel)
                    statusMessage = "✅ AI configuration saved successfully!"
                    isSuccessStatus = true
                },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            ) {
                Icon(Icons.Default.Save, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text("Save AI Settings")
            }
        }
    }
}

