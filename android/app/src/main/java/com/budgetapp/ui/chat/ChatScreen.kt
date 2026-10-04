package com.budgetapp.ui.chat

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AddCard
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Key
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import com.budgetapp.data.local.entity.TransactionEntity
import com.budgetapp.ui.theme.GreenSuccess
import com.budgetapp.ui.theme.PrimaryBlue
import com.budgetapp.ui.theme.Slate400
import kotlinx.coroutines.launch
import org.json.JSONObject

data class ChatMessage(
    val sender: String, // "user" or "ai"
    val text: String,
    val transactionAction: TransactionEntity? = null
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    messages: List<ChatMessage>,
    isLoading: Boolean,
    hasApiKey: Boolean,
    onSendMessage: (String) -> Unit,
    onConfirmActionTransaction: (TransactionEntity) -> Unit,
    onConfigureApiKey: () -> Unit,
    modifier: Modifier = Modifier
) {
    var inputText by remember { mutableStateOf("") }
    val listState = rememberLazyListState()
    val coroutineScope = rememberCoroutineScope()

    val suggestionChips = listOf(
        "🩺 Run Financial Health Audit",
        "💡 How much can I spend today?",
        "📊 Where is my money going?",
        "🛡️ Check emergency runway"
    )

    Column(modifier = modifier.fillMaxSize()) {
        if (!hasApiKey) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(8.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Key, contentDescription = null, tint = MaterialTheme.colorScheme.onErrorContainer)
                        Text("Gemini API Key Needed", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
                    }
                    TextButton(onClick = onConfigureApiKey) {
                        Text("Configure")
                    }
                }
            }
        }

        LazyColumn(
            state = listState,
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            if (messages.isEmpty()) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(40.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            Icon(Icons.Default.AutoAwesome, contentDescription = null, tint = PrimaryBlue, modifier = Modifier.size(48.dp))
                            Text("BudgetApp AI Assistant", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Text(
                                "Ask questions about your budget, spending trends, or request an instant financial audit.",
                                style = MaterialTheme.typography.bodySmall,
                                color = Slate400
                            )
                        }
                    }
                }
            }

            items(messages) { msg ->
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    ChatBubble(message = msg)
                    // If AI proposed a transaction, show 1-click confirmation card
                    msg.transactionAction?.let { tx ->
                        TransactionConfirmationCard(
                            transaction = tx,
                            onConfirm = { onConfirmActionTransaction(tx) }
                        )
                    }
                }
            }

            if (isLoading) {
                item {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 8.dp),
                        horizontalArrangement = Arrangement.Start
                    ) {
                        CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Analyzing budget...", style = MaterialTheme.typography.bodySmall, color = Slate400)
                    }
                }
            }
        }

        // Suggestion Chips
        LazyRow(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(suggestionChips) { chipText ->
                SuggestionChip(
                    onClick = {
                        val cleanPrompt = chipText.replace("🩺 ", "").replace("💡 ", "").replace("📊 ", "").replace("🛡️ ", "")
                        onSendMessage(cleanPrompt)
                    },
                    label = { Text(chipText, style = MaterialTheme.typography.labelSmall) }
                )
            }
        }

        // Input Field
        Surface(
            modifier = Modifier.fillMaxWidth(),
            tonalElevation = 2.dp
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedTextField(
                    value = inputText,
                    onValueChange = { inputText = it },
                    placeholder = { Text("Ask Budget AI...") },
                    modifier = Modifier.weight(1f),
                    singleLine = true,
                    shape = RoundedCornerShape(24.dp)
                )

                IconButton(
                    onClick = {
                        if (inputText.isNotBlank() && !isLoading) {
                            val textToSend = inputText.trim()
                            inputText = ""
                            onSendMessage(textToSend)
                            coroutineScope.launch {
                                listState.animateScrollToItem(messages.size)
                            }
                        }
                    },
                    enabled = inputText.isNotBlank() && !isLoading
                ) {
                    Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Send", tint = MaterialTheme.colorScheme.primary)
                }
            }
        }
    }
}

@Composable
fun ChatBubble(message: ChatMessage) {
    val isUser = message.sender == "user"
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start
    ) {
        Card(
            shape = RoundedCornerShape(
                topStart = 16.dp,
                topEnd = 16.dp,
                bottomStart = if (isUser) 16.dp else 4.dp,
                bottomEnd = if (isUser) 4.dp else 16.dp
            ),
            colors = CardDefaults.cardColors(
                containerColor = if (isUser) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant
            ),
            modifier = Modifier.widthIn(max = 340.dp)
        ) {
            Box(modifier = Modifier.padding(12.dp)) {
                if (isUser) {
                    Text(
                        text = message.text,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                } else {
                    MarkdownMessageContent(
                        content = message.text,
                        textColor = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}

/**
 * Parses and renders Markdown with support for:
 * - Bold (**text**) and Italics (*text*)
 * - Inline code (`code`)
 * - Bullet list items (•, -, *)
 * - Markdown tables (| Col 1 | Col 2 |) with responsive horizontal scrolling
 */
@Composable
fun MarkdownMessageContent(
    content: String,
    textColor: Color,
    modifier: Modifier = Modifier
) {
    val lines = remember(content) { content.lines() }

    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        var inTable = false
        val currentTableRows = mutableListOf<List<String>>()
        var i = 0
        while (i < lines.size) {
            val line = lines[i]
            val trimmed = line.trim()

            // Check for Markdown table line (contains | and starts/ends or splits with |)
            val isTableRow = trimmed.startsWith("|") && trimmed.endsWith("|") && trimmed.count { it == '|' } >= 2

            if (isTableRow) {
                // Ignore markdown separator row (|---|---|)
                val isSeparator = trimmed.replace("|", "").replace("-", "").replace(":", "").trim().isEmpty()
                if (!isSeparator) {
                    val cells = trimmed.split("|")
                        .drop(1)
                        .dropLast(1)
                        .map { it.trim() }
                    currentTableRows.add(cells)
                }
                inTable = true
            } else {
                if (inTable) {
                    val rowsToRender = currentTableRows.toList()
                    currentTableRows.clear()
                    inTable = false
                    MarkdownTableView(rows = rowsToRender, textColor = textColor)
                }

                if (trimmed.isNotEmpty()) {
                    val isBullet = trimmed.startsWith("•") || trimmed.startsWith("- ") || trimmed.startsWith("* ")
                    val displayText = if (isBullet) {
                        val clean = when {
                            trimmed.startsWith("- ") -> trimmed.removePrefix("- ")
                            trimmed.startsWith("* ") -> trimmed.removePrefix("* ")
                            trimmed.startsWith("• ") -> trimmed.removePrefix("• ")
                            trimmed.startsWith("•") -> trimmed.removePrefix("•")
                            else -> trimmed
                        }
                        "• $clean"
                    } else {
                        trimmed
                    }

                    val annotatedText = parseMarkdownInText(displayText, textColor)
                    Text(
                        text = annotatedText,
                        style = MaterialTheme.typography.bodyMedium,
                        color = textColor
                    )
                }
            }
            i++
        }

        // Flush any trailing table
        if (currentTableRows.isNotEmpty()) {
            MarkdownTableView(rows = currentTableRows, textColor = textColor)
        }
    }
}

/**
 * Parses inline markdown: **bold**, *italic*, `code` into AnnotatedString.
 */
@Composable
fun parseMarkdownInText(text: String, baseColor: Color): androidx.compose.ui.text.AnnotatedString {
    return remember(text, baseColor) {
        buildAnnotatedString {
            // Regex to find **bold**, *italic*, or `code`
            val pattern = Regex("""(\*\*.*?\*\*|\*.*?\*|`.*?`)""")
            var currentIndex = 0

            val matches = pattern.findAll(text)
            for (match in matches) {
                // Append text before match
                if (match.range.first > currentIndex) {
                    append(text.substring(currentIndex, match.range.first))
                }

                val token = match.value
                when {
                    token.startsWith("**") && token.endsWith("**") && token.length >= 4 -> {
                        withStyle(SpanStyle(fontWeight = FontWeight.Bold)) {
                            append(token.substring(2, token.length - 2))
                        }
                    }
                    token.startsWith("`") && token.endsWith("`") && token.length >= 2 -> {
                        withStyle(
                            SpanStyle(
                                fontFamily = FontFamily.Monospace,
                                background = baseColor.copy(alpha = 0.12f),
                                fontWeight = FontWeight.SemiBold
                            )
                        ) {
                            append(token.substring(1, token.length - 1))
                        }
                    }
                    token.startsWith("*") && token.endsWith("*") && token.length >= 2 -> {
                        withStyle(SpanStyle(fontStyle = FontStyle.Italic)) {
                            append(token.substring(1, token.length - 1))
                        }
                    }
                    else -> append(token)
                }

                currentIndex = match.range.last + 1
            }

            if (currentIndex < text.length) {
                append(text.substring(currentIndex))
            }
        }
    }
}

/**
 * Beautifully styled Markdown Table with horizontal scrolling and alternating row tint.
 */
@Composable
fun MarkdownTableView(
    rows: List<List<String>>,
    textColor: Color,
    modifier: Modifier = Modifier
) {
    if (rows.isEmpty()) return
    val scrollState = rememberScrollState()

    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = CardDefaults.outlinedCardBorder()
    ) {
        Column(
            modifier = Modifier
                .horizontalScroll(scrollState)
                .padding(6.dp)
        ) {
            rows.forEachIndexed { rowIndex, cells ->
                val isHeader = rowIndex == 0
                Row(
                    modifier = Modifier
                        .padding(vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    cells.forEachIndexed { colIndex, cellText ->
                        Box(
                            modifier = Modifier
                                .widthIn(min = 80.dp, max = 160.dp)
                                .padding(horizontal = 8.dp)
                        ) {
                            val annotated = parseMarkdownInText(cellText, textColor)
                            Text(
                                text = annotated,
                                style = if (isHeader) MaterialTheme.typography.labelMedium else MaterialTheme.typography.bodySmall,
                                fontWeight = if (isHeader) FontWeight.Bold else FontWeight.Normal,
                                color = if (isHeader) MaterialTheme.colorScheme.primary else textColor
                            )
                        }
                    }
                }
                if (isHeader) {
                    HorizontalDivider(
                        color = MaterialTheme.colorScheme.outlineVariant,
                        thickness = 1.dp,
                        modifier = Modifier.padding(vertical = 2.dp)
                    )
                }
            }
        }
    }
}

@Composable
fun TransactionConfirmationCard(
    transaction: TransactionEntity,
    onConfirm: () -> Unit
) {
    var confirmed by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        shape = RoundedCornerShape(10.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.5f))
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
                    text = "Suggested Transaction",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
                Text(
                    text = "${transaction.description ?: "Transaction"} • $${String.format("%.2f", transaction.amount)}",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold
                )
            }

            Button(
                onClick = {
                    if (!confirmed) {
                        confirmed = true
                        onConfirm()
                    }
                },
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (confirmed) GreenSuccess else MaterialTheme.colorScheme.primary
                ),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
            ) {
                Icon(
                    imageVector = if (confirmed) Icons.Default.Check else Icons.Default.AddCard,
                    contentDescription = null,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(if (confirmed) "Added!" else "Confirm & Log", style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ApiKeyDialog(
    currentApiKey: String,
    currentModel: String,
    onDismiss: () -> Unit,
    onSave: (key: String, model: String) -> Unit
) {
    var apiKeyText by remember { mutableStateOf(currentApiKey) }
    var selectedModel by remember { mutableStateOf(currentModel.ifBlank { com.budgetapp.domain.ai.GeminiAssistant.DEFAULT_MODEL }) }
    var modelDropdownExpanded by remember { mutableStateOf(false) }
    var availableModels by remember { mutableStateOf(com.budgetapp.domain.ai.GeminiAssistant.DEFAULT_MODELS) }
    var isDetectingModels by remember { mutableStateOf(false) }
    var detectStatus by remember { mutableStateOf<String?>(null) }
    val coroutineScope = rememberCoroutineScope()

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("🔑 Gemini AI Configuration", fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(
                    "Enter your Google Gemini API key to enable live budget intelligence. Your key is stored securely in your device's local database.",
                    style = MaterialTheme.typography.bodySmall
                )
                OutlinedTextField(
                    value = apiKeyText,
                    onValueChange = { apiKeyText = it },
                    label = { Text("Gemini API Key") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                ExposedDropdownMenuBox(
                    expanded = modelDropdownExpanded,
                    onExpandedChange = { modelDropdownExpanded = !modelDropdownExpanded }
                ) {
                    OutlinedTextField(
                        value = selectedModel,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Model") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = modelDropdownExpanded) },
                        modifier = Modifier.fillMaxWidth().menuAnchor()
                    )
                    ExposedDropdownMenu(
                        expanded = modelDropdownExpanded,
                        onDismissRequest = { modelDropdownExpanded = false }
                    ) {
                        availableModels.forEach { m ->
                            DropdownMenuItem(
                                text = { Text(m, fontWeight = if (m == selectedModel) FontWeight.Bold else FontWeight.Normal) },
                                onClick = {
                                    selectedModel = m
                                    modelDropdownExpanded = false
                                }
                            )
                        }
                    }
                }

                OutlinedButton(
                    onClick = {
                        if (apiKeyText.isBlank()) {
                            detectStatus = "Please enter an API key first."
                            return@OutlinedButton
                        }
                        isDetectingModels = true
                        detectStatus = "Querying Gemini API..."
                        coroutineScope.launch {
                            val discovered = com.budgetapp.domain.ai.GeminiAssistant.fetchAvailableModels(apiKeyText.trim())
                            isDetectingModels = false
                            if (discovered.isNotEmpty()) {
                                availableModels = discovered
                                if (!discovered.contains(selectedModel)) {
                                    selectedModel = discovered.first()
                                }
                                detectStatus = "✅ Found ${discovered.size} model(s)."
                            } else {
                                detectStatus = "Could not discover models."
                            }
                        }
                    },
                    enabled = !isDetectingModels,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    if (isDetectingModels) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Detecting...")
                    } else {
                        Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Auto-Detect Models")
                    }
                }

                detectStatus?.let { msg ->
                    Text(msg, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary)
                }
            }
        },
        confirmButton = {
            Button(onClick = { onSave(apiKeyText.trim(), selectedModel) }) {
                Text("Save")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}
