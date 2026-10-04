package com.budgetapp

import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Flag
import androidx.compose.material.icons.filled.Settings
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.budgetapp.data.local.entity.CategoryEntity
import com.budgetapp.data.local.entity.RecurringTransactionEntity
import com.budgetapp.data.local.entity.SavingsGoalEntity
import com.budgetapp.data.local.entity.TransactionEntity
import com.budgetapp.domain.ai.AiContextSynthesizer
import com.budgetapp.domain.ai.GeminiAssistant
import com.budgetapp.domain.calculator.BudgetCalculator
import com.budgetapp.domain.csv.CsvEngine
import com.budgetapp.ui.chat.ApiKeyDialog
import com.budgetapp.ui.chat.ChatMessage
import com.budgetapp.ui.chat.ChatScreen
import com.budgetapp.ui.dashboard.CategoryReallocationDialog
import com.budgetapp.ui.dashboard.DashboardScreen
import com.budgetapp.ui.goals.CreateGoalDialog
import com.budgetapp.ui.goals.GoalContributeDialog
import com.budgetapp.ui.goals.SavingsGoalsScreen
import com.budgetapp.ui.settings.SettingsScreen
import com.budgetapp.ui.theme.BudgetAppTheme
import com.budgetapp.ui.transactions.AddTransactionDialog
import com.budgetapp.ui.transactions.EditTransactionDialog
import com.budgetapp.ui.transactions.TransactionListScreen
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.time.LocalDate

class MainActivity : ComponentActivity() {

    @OptIn(ExperimentalMaterial3Api::class)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val app = application as BudgetApplication
        val repo = app.repository

        setContent {
            val coroutineScope = rememberCoroutineScope()
            var currencySymbol by remember { mutableStateOf("$") }
            var isPrivacyMode by remember { mutableStateOf(false) }
            var geminiApiKey by remember { mutableStateOf("") }
            var geminiModel by remember { mutableStateOf("gemini-1.5-flash") }

            // Load initial settings
            LaunchedEffect(Unit) {
                currencySymbol = repo.getSetting("currency_symbol") ?: "$"
                isPrivacyMode = (repo.getSetting("privacy_mode") ?: "0") == "1"
                geminiApiKey = repo.getSetting("gemini_api_key") ?: ""
                geminiModel = repo.getSetting("gemini_model") ?: "gemini-1.5-flash"
            }

            BudgetAppTheme {
                val context = LocalContext.current
                var selectedTab by remember { mutableIntStateOf(0) }

                // Dialog states
                var showAddDialog by remember { mutableStateOf(false) }
                var showReallocateDialog by remember { mutableStateOf(false) }
                var showCreateGoalDialog by remember { mutableStateOf(false) }
                var showApiKeyDialog by remember { mutableStateOf(false) }
                var goalToContribute by remember { mutableStateOf<SavingsGoalEntity?>(null) }
                var transactionToEdit by remember { mutableStateOf<TransactionEntity?>(null) }
                var monthMenuExpanded by remember { mutableStateOf(false) }

                val currentRealMonth = remember { LocalDate.now().toString().substring(0, 7) }
                var activeMonth by remember { mutableStateOf(currentRealMonth) }

                // Database state flows
                val categories by repo.getAllCategories().collectAsState(initial = emptyList())
                val transactions by repo.getAllTransactions().collectAsState(initial = emptyList())
                val pendingTransactions by repo.getPendingApprovalTransactions().collectAsState(initial = emptyList())
                val emergencyFund by repo.getEmergencyFund().collectAsState(initial = null)
                val emergencyLogs by repo.getEmergencyFundLogs().collectAsState(initial = emptyList())
                val goals by repo.getAllGoals().collectAsState(initial = emptyList())
                val recurringList by repo.getAllRecurring().collectAsState(initial = emptyList())
                val savingsList by repo.getAllSavings().collectAsState(initial = emptyList())

                // Historical trend data (6 months) & Archives ledger
                var historicalTrend by remember { mutableStateOf<List<com.budgetapp.domain.model.HistoricalTrendPoint>>(emptyList()) }
                var archivesList by remember { mutableStateOf<List<com.budgetapp.domain.model.MonthArchiveRecord>>(emptyList()) }

                LaunchedEffect(transactions, savingsList) {
                    historicalTrend = repo.getHistoricalTrend(monthsCount = 6)
                    archivesList = repo.getClosedMonthsLedger()
                }

                // AI Chat State
                val chatMessages = remember { mutableStateListOf<ChatMessage>() }
                var isAiLoading by remember { mutableStateOf(false) }

                // Distinct available months for Time Machine selector
                val availableMonths = remember(transactions, savingsList) {
                    val monthsSet = transactions.mapNotNull {
                        if (it.date.length >= 7) it.date.substring(0, 7) else null
                    }.toMutableSet()
                    savingsList.forEach { s ->
                        if (s.month.length >= 7) monthsSet.add(s.month)
                    }
                    monthsSet.add(currentRealMonth)
                    monthsSet.sortedDescending()
                }

                // Derived monthly summary for activeMonth
                val summary = remember(activeMonth, categories, transactions, emergencyFund, savingsList) {
                    val monthTx = transactions.filter { tx -> tx.date.startsWith(activeMonth) }
                    val activeSavings = savingsList.find { it.month == activeMonth }
                    BudgetCalculator.calculateMonthlySummary(
                        month = activeMonth,
                        categories = categories,
                        transactions = monthTx,
                        savingsBalance = savingsList.sumOf { it.rolloverAmount },
                        emergencyFundBalance = emergencyFund?.balance ?: 0.0,
                        isClosed = activeSavings != null,
                        rolloverAmount = activeSavings?.rolloverAmount ?: 0.0
                    )
                }


                // CSV Export Launcher
                val exportCsvLauncher = rememberLauncherForActivityResult(
                    contract = ActivityResultContracts.CreateDocument("text/csv")
                ) { uri: Uri? ->
                    uri?.let { destUri ->
                        coroutineScope.launch(Dispatchers.IO) {
                            try {
                                context.contentResolver.openOutputStream(destUri)?.use { out ->
                                    CsvEngine.exportTransactionsToCsv(out, transactions, categories)
                                }
                                withContext(Dispatchers.Main) {
                                    Toast.makeText(context, "Exported ${transactions.size} transactions to CSV", Toast.LENGTH_SHORT).show()
                                }
                            } catch (e: Exception) {
                                withContext(Dispatchers.Main) {
                                    Toast.makeText(context, "Export failed: ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
                                }
                            }
                        }
                    }
                }

                // CSV Import Launcher
                val importCsvLauncher = rememberLauncherForActivityResult(
                    contract = ActivityResultContracts.OpenDocument()
                ) { uri: Uri? ->
                    uri?.let { srcUri ->
                        coroutineScope.launch(Dispatchers.IO) {
                            try {
                                val parseResult = context.contentResolver.openInputStream(srcUri)?.use { stream ->
                                    CsvEngine.parseCsvInputStream(stream, categories)
                                }
                                if (parseResult != null && parseResult.transactions.isNotEmpty()) {
                                    repo.insertTransactions(parseResult.transactions)
                                    withContext(Dispatchers.Main) {
                                        Toast.makeText(
                                            context,
                                            "Imported ${parseResult.validRows} transactions (${parseResult.errorCount} skipped)",
                                            Toast.LENGTH_LONG
                                        ).show()
                                    }
                                } else {
                                    withContext(Dispatchers.Main) {
                                        Toast.makeText(context, parseResult?.errorMessage ?: "No valid rows found in CSV", Toast.LENGTH_SHORT).show()
                                    }
                                }
                            } catch (e: Exception) {
                                withContext(Dispatchers.Main) {
                                    Toast.makeText(context, "Import error: ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
                                }
                            }
                        }
                    }
                }

                Scaffold(
                    topBar = {
                        TopAppBar(
                            title = {
                                val titleText = when (selectedTab) {
                                    0 -> "Dashboard ($activeMonth)"
                                    1 -> "Transactions"
                                    2 -> "Savings Goals"
                                    3 -> "AI Financial Assistant"
                                    4 -> "Settings"
                                    else -> "BudgetApp"
                                }
                                Text(
                                    text = titleText,
                                    style = MaterialTheme.typography.titleLarge,
                                    fontWeight = FontWeight.Bold
                                )
                            },
                            actions = {
                                if (selectedTab == 0 && availableMonths.size > 1) {
                                    Box {
                                        FilledTonalIconButton(
                                            onClick = { monthMenuExpanded = true },
                                            modifier = Modifier.padding(end = 8.dp)
                                        ) {
                                            Icon(Icons.Default.CalendarMonth, contentDescription = "Select Month")
                                        }
                                        DropdownMenu(
                                            expanded = monthMenuExpanded,
                                            onDismissRequest = { monthMenuExpanded = false }
                                        ) {
                                            availableMonths.forEach { m ->
                                                DropdownMenuItem(
                                                    text = {
                                                        Text(
                                                            text = if (m == currentRealMonth) "$m (Current)" else m,
                                                            fontWeight = if (m == activeMonth) FontWeight.Bold else FontWeight.Normal
                                                        )
                                                    },
                                                    onClick = {
                                                        activeMonth = m
                                                        monthMenuExpanded = false
                                                    }
                                                )
                                            }
                                        }
                                    }
                                }
                            },
                            colors = TopAppBarDefaults.topAppBarColors(
                                containerColor = MaterialTheme.colorScheme.surface,
                                titleContentColor = MaterialTheme.colorScheme.onSurface
                            )
                        )
                    },
                    bottomBar = {
                        NavigationBar(
                            containerColor = MaterialTheme.colorScheme.surface,
                            tonalElevation = 6.dp
                        ) {
                            NavigationBarItem(
                                selected = selectedTab == 0,
                                onClick = { selectedTab = 0 },
                                icon = { Icon(Icons.Default.Dashboard, contentDescription = "Dashboard") },
                                label = { Text("Dashboard", style = MaterialTheme.typography.labelSmall) }
                            )
                            NavigationBarItem(
                                selected = selectedTab == 1,
                                onClick = { selectedTab = 1 },
                                icon = { Icon(Icons.AutoMirrored.Filled.List, contentDescription = "Transactions") },
                                label = { Text("Ledger", style = MaterialTheme.typography.labelSmall) }
                            )
                            NavigationBarItem(
                                selected = selectedTab == 2,
                                onClick = { selectedTab = 2 },
                                icon = { Icon(Icons.Default.Flag, contentDescription = "Goals") },
                                label = { Text("Goals", style = MaterialTheme.typography.labelSmall) }
                            )
                            NavigationBarItem(
                                selected = selectedTab == 3,
                                onClick = { selectedTab = 3 },
                                icon = { Icon(Icons.Default.AutoAwesome, contentDescription = "AI Assistant") },
                                label = { Text("AI", style = MaterialTheme.typography.labelSmall) }
                            )
                            NavigationBarItem(
                                selected = selectedTab == 4,
                                onClick = { selectedTab = 4 },
                                icon = { Icon(Icons.Default.Settings, contentDescription = "Settings") },
                                label = { Text("Settings", style = MaterialTheme.typography.labelSmall) }
                            )
                        }
                    },
                    floatingActionButton = {
                        if (selectedTab == 0 || selectedTab == 1) {
                            FloatingActionButton(
                                onClick = { showAddDialog = true },
                                containerColor = MaterialTheme.colorScheme.primary,
                                contentColor = MaterialTheme.colorScheme.onPrimary,
                                shape = RoundedCornerShape(16.dp)
                            ) {
                                Icon(Icons.Default.Add, contentDescription = "Add Transaction")
                            }
                        }
                    }
                ) { innerPadding ->
                    Box(modifier = Modifier.padding(innerPadding)) {
                        when (selectedTab) {
                            0 -> DashboardScreen(
                                summary = summary,
                                historicalTrend = historicalTrend,
                                currencySymbol = currencySymbol,
                                isPrivacyMode = isPrivacyMode,
                                isArchiveMonth = activeMonth != currentRealMonth,
                                onOpenReallocate = { showReallocateDialog = true }
                            )
                            1 -> TransactionListScreen(
                                transactions = transactions,
                                pendingTransactions = pendingTransactions,
                                categories = categories,
                                currencySymbol = currencySymbol,
                                isPrivacyMode = isPrivacyMode,
                                onApprovePending = { id ->
                                    coroutineScope.launch { repo.approveTransaction(id) }
                                },
                                onDeleteTransaction = { tx ->
                                    coroutineScope.launch { repo.deleteTransaction(tx) }
                                },
                                onEditTransaction = { tx -> transactionToEdit = tx },
                                onExportCsv = {
                                    exportCsvLauncher.launch("budget_transactions_${LocalDate.now()}.csv")
                                },
                                onImportCsv = {
                                    importCsvLauncher.launch(arrayOf("text/csv", "text/comma-separated-values", "application/csv", "*/*"))
                                }
                            )
                            2 -> SavingsGoalsScreen(
                                goals = goals,
                                currencySymbol = currencySymbol,
                                isPrivacyMode = isPrivacyMode,
                                onCreateGoal = { showCreateGoalDialog = true },
                                onContribute = { goalToContribute = it },
                                onDeleteGoal = { goal ->
                                    coroutineScope.launch { repo.deleteGoal(goal) }
                                }
                            )
                            3 -> ChatScreen(
                                messages = chatMessages,
                                isLoading = isAiLoading,
                                hasApiKey = geminiApiKey.isNotBlank(),
                                onSendMessage = { userText ->
                                    chatMessages.add(ChatMessage("user", userText))
                                    isAiLoading = true
                                    coroutineScope.launch(Dispatchers.IO) {
                                        val contextPrompt = AiContextSynthesizer.buildFinancialContext(
                                            summary = summary,
                                            categories = categories,
                                            transactions = transactions,
                                            goals = goals,
                                            emergencyFund = emergencyFund,
                                            currencySymbol = currencySymbol
                                        )
                                        val assistant = GeminiAssistant(geminiApiKey, geminiModel)
                                        assistant.streamChatResponse(userText, contextPrompt).collect { rawResponse ->
                                            var cleanText = rawResponse
                                            var parsedTx: TransactionEntity? = null

                                            // Extract action JSON if present
                                            val actionRegex = Regex("""```(?:json)?\s*(\{.*?"action"\s*:\s*"add_transaction".*?\})\s*```""", RegexOption.DOT_MATCHES_ALL)
                                            val match = actionRegex.find(rawResponse)
                                            if (match != null) {
                                                try {
                                                    val jsonStr = match.groupValues[1]
                                                    val obj = JSONObject(jsonStr)
                                                    val amt = obj.optDouble("amount", 0.0)
                                                    val type = obj.optString("type", "expense")
                                                    val catName = obj.optString("category", "")
                                                    val desc = obj.optString("description", "")
                                                    val date = obj.optString("date", LocalDate.now().toString())

                                                    val catId = categories.find { it.name.equals(catName, ignoreCase = true) }?.id
                                                        ?: categories.firstOrNull()?.id

                                                    parsedTx = TransactionEntity(
                                                        date = date,
                                                        amount = amt,
                                                        type = type,
                                                        categoryId = catId,
                                                        description = desc,
                                                        status = "confirmed"
                                                    )
                                                    cleanText = rawResponse.substring(0, match.range.first).trim()
                                                } catch (e: Exception) {
                                                    // parsing failed, leave cleanText as is
                                                }
                                            }

                                            withContext(Dispatchers.Main) {
                                                chatMessages.add(ChatMessage("ai", cleanText, parsedTx))
                                                isAiLoading = false
                                            }
                                        }
                                    }
                                },
                                onConfirmActionTransaction = { actionTx ->
                                    coroutineScope.launch {
                                        repo.insertTransaction(actionTx)
                                        Toast.makeText(context, "Transaction confirmed & logged into ledger!", Toast.LENGTH_SHORT).show()
                                    }
                                },
                                onConfigureApiKey = { showApiKeyDialog = true }
                            )
                            4 -> SettingsScreen(
                                categories = categories,
                                emergencyFund = emergencyFund,
                                emergencyLogs = emergencyLogs,
                                recurringList = recurringList,
                                currencySymbol = currencySymbol,
                                isPrivacyMode = isPrivacyMode,
                                onUpdateCurrency = { newSym ->
                                    currencySymbol = newSym
                                    coroutineScope.launch { repo.setSetting("currency_symbol", newSym) }
                                },
                                onTogglePrivacy = { newPriv ->
                                    isPrivacyMode = newPriv
                                    coroutineScope.launch { repo.setSetting("privacy_mode", if (newPriv) "1" else "0") }
                                },
                                onAddCategory = { name, soft, hard ->
                                    coroutineScope.launch {
                                        repo.insertCategory(
                                            CategoryEntity(name = name, softLimit = soft, hardLimit = hard, createdAt = LocalDate.now().toString())
                                        )
                                    }
                                },
                                onEditCategory = { cat ->
                                    coroutineScope.launch { repo.updateCategory(cat) }
                                },
                                onDeleteCategory = { cat ->
                                    coroutineScope.launch { repo.deleteCategory(cat) }
                                },
                                onDepositEmergencyFund = { amt, note ->
                                    coroutineScope.launch { repo.depositEmergencyFund(amt, note) }
                                },
                                onWithdrawEmergencyFund = { amt, note ->
                                    coroutineScope.launch { repo.withdrawEmergencyFund(amt, note) }
                                },
                                onSaveRecurringRule = { rule ->
                                    coroutineScope.launch {
                                        if (rule.id == 0L) {
                                            repo.insertRecurring(rule)
                                        } else {
                                            repo.updateRecurring(rule)
                                        }
                                    }
                                },
                                onDeleteRecurring = { rule ->
                                    coroutineScope.launch { repo.deleteRecurring(rule) }
                                },
                                onManualRollover = {
                                    coroutineScope.launch {
                                        val rolled = repo.autoRunAllPastRollovers()
                                        archivesList = repo.getClosedMonthsLedger()
                                        if (rolled.isNotEmpty()) {
                                            Toast.makeText(context, "Rolled over: ${rolled.joinToString()}", Toast.LENGTH_SHORT).show()
                                        } else {
                                            Toast.makeText(context, "All past months up to date", Toast.LENGTH_SHORT).show()
                                        }
                                    }
                                },
                                archivesList = archivesList,
                                onViewArchiveInDashboard = { archiveMonth ->
                                    activeMonth = archiveMonth
                                    selectedTab = 0
                                }
                            )
                        }
                    }

                    // Reallocation Dialog
                    if (showReallocateDialog) {
                        CategoryReallocationDialog(
                            categories = categories,
                            onDismiss = { showReallocateDialog = false },
                            onTransfer = { fromId, toId, amt ->
                                coroutineScope.launch {
                                    try {
                                        repo.transferCategoryBudget(fromId, toId, amt)
                                        showReallocateDialog = false
                                        Toast.makeText(context, "Budget reallocated successfully", Toast.LENGTH_SHORT).show()
                                    } catch (e: Exception) {
                                        Toast.makeText(context, e.localizedMessage ?: "Transfer failed", Toast.LENGTH_SHORT).show()
                                    }
                                }
                            }
                        )
                    }

                    // Add Transaction Dialog
                    if (showAddDialog) {
                        AddTransactionDialog(
                            categories = categories,
                            onDismiss = { showAddDialog = false },
                            onSaveSingle = { newTx ->
                                coroutineScope.launch {
                                    repo.insertTransaction(newTx)
                                    showAddDialog = false
                                }
                            },
                            onSaveSplit = { date, desc, splits, fundingSource ->
                                coroutineScope.launch {
                                    repo.createSplitTransaction(date, desc, splits, fundingSource)
                                    showAddDialog = false
                                }
                            }
                        )
                    }

                    // Edit Transaction Dialog
                    transactionToEdit?.let { tx ->
                        EditTransactionDialog(
                            transaction = tx,
                            categories = categories,
                            onDismiss = { transactionToEdit = null },
                            onSave = { updatedTx ->
                                coroutineScope.launch {
                                    repo.updateTransaction(updatedTx)
                                    transactionToEdit = null
                                }
                            }
                        )
                    }

                    // Create Goal Dialog
                    if (showCreateGoalDialog) {
                        CreateGoalDialog(
                            onDismiss = { showCreateGoalDialog = false },
                            onSave = { name, target, date ->
                                coroutineScope.launch {
                                    repo.insertGoal(
                                        SavingsGoalEntity(
                                            name = name,
                                            targetAmount = target,
                                            targetDate = date,
                                            createdAt = LocalDate.now().toString()
                                        )
                                    )
                                    showCreateGoalDialog = false
                                }
                            }
                        )
                    }

                    // Contribute to Goal Dialog
                    goalToContribute?.let { goal ->
                        GoalContributeDialog(
                            goal = goal,
                            currencySymbol = currencySymbol,
                            onDismiss = { goalToContribute = null },
                            onConfirm = { amt, note ->
                                coroutineScope.launch {
                                    repo.contributeToGoal(goal.id, amt, note)
                                    goalToContribute = null
                                }
                            }
                        )
                    }

                    // API Key & Model Dialog
                    if (showApiKeyDialog) {
                        ApiKeyDialog(
                            currentApiKey = geminiApiKey,
                            currentModel = geminiModel,
                            onDismiss = { showApiKeyDialog = false },
                            onSave = { newKey, newModel ->
                                geminiApiKey = newKey
                                geminiModel = newModel
                                coroutineScope.launch {
                                    repo.setSetting("gemini_api_key", newKey)
                                    repo.setSetting("gemini_model", newModel)
                                    showApiKeyDialog = false
                                    Toast.makeText(context, "AI settings saved ($newModel)", Toast.LENGTH_SHORT).show()
                                }
                            }
                        )
                    }
                }
            }
        }
    }
}
