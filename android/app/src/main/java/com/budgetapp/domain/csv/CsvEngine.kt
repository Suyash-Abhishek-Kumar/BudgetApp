package com.budgetapp.domain.csv

import com.budgetapp.data.local.entity.CategoryEntity
import com.budgetapp.data.local.entity.TransactionEntity
import java.io.BufferedReader
import java.io.InputStream
import java.io.InputStreamReader
import java.io.OutputStream
import java.io.OutputStreamWriter
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

object CsvEngine {

    data class CsvParseResult(
        val transactions: List<TransactionEntity>,
        val totalRows: Int,
        val validRows: Int,
        val errorCount: Int,
        val errorMessage: String? = null
    )

    fun exportTransactionsToCsv(
        outputStream: OutputStream,
        transactions: List<TransactionEntity>,
        categories: List<CategoryEntity>
    ) {
        val catMap = categories.associateBy { it.id }
        OutputStreamWriter(outputStream, Charsets.UTF_8).use { writer ->
            // Write Excel-friendly UTF-8 BOM
            writer.write("\uFEFF")
            writer.write("Date,Category,Description,Amount,Type,Funding Source,Status\n")
            for (tx in transactions) {
                val catName = catMap[tx.categoryId]?.name ?: if (tx.type == "income") "General Income" else ""
                val cleanDesc = (tx.description ?: "").replace("\"", "\"\"")
                writer.write(
                    String.format(
                        Locale.US,
                        "\"%s\",\"%s\",\"%s\",%.2f,\"%s\",\"%s\",\"%s\"\n",
                        tx.date,
                        catName,
                        cleanDesc,
                        tx.amount,
                        tx.type,
                        tx.fundingSource,
                        tx.status
                    )
                )
            }
            writer.flush()
        }
    }

    fun parseCsvInputStream(
        inputStream: InputStream,
        categories: List<CategoryEntity>,
        defaultCategoryId: Long? = null
    ): CsvParseResult {
        val catByName = categories.associateBy { it.name.lowercase().trim() }
        val parsedList = mutableListOf<TransactionEntity>()
        var errorCount = 0

        BufferedReader(InputStreamReader(inputStream, Charsets.UTF_8)).use { reader ->
            val headerLine = reader.readLine() ?: return CsvParseResult(emptyList(), 0, 0, 0, "File is empty")
            val headers = splitCsvLine(headerLine)
            val mapping = detectColumns(headers)

            var line: String?
            while (reader.readLine().also { line = it } != null) {
                val currentLine = line!!.trim()
                if (currentLine.isEmpty()) continue

                val cols = splitCsvLine(currentLine)
                val rowDict = mutableMapOf<String, String>()
                for (i in headers.indices) {
                    if (i < cols.size) {
                        rowDict[headers[i].trim()] = cols[i].trim()
                    }
                }

                // Date
                val rawDate = mapping["date"]?.let { rowDict[it] } ?: ""
                val parsedDate = parseDateString(rawDate) ?: LocalDate.now().toString()

                // Description
                val desc = mapping["description"]?.let { rowDict[it] } ?: ""

                // Amount & Type
                var amount: Double? = null
                var type = "expense"

                val debitCol = mapping["debit"]
                val creditCol = mapping["credit"]
                val amountCol = mapping["amount"]
                val typeCol = mapping["type"]

                if (debitCol != null && creditCol != null) {
                    val debitVal = parseAmountString(rowDict[debitCol])
                    val creditVal = parseAmountString(rowDict[creditCol])
                    if (debitVal != null && debitVal > 0) {
                        amount = debitVal
                        type = "expense"
                    } else if (creditVal != null && creditVal > 0) {
                        amount = creditVal
                        type = "income"
                    }
                } else if (amountCol != null) {
                    val rawAmt = parseAmountString(rowDict[amountCol])
                    if (rawAmt != null) {
                        if (rawAmt < 0) {
                            amount = kotlin.math.abs(rawAmt)
                            type = "expense"
                        } else {
                            amount = rawAmt
                            val rawType = typeCol?.let { rowDict[it]?.lowercase() } ?: ""
                            type = if (rawType.contains("cr") || rawType.contains("credit") || rawType.contains("income")) {
                                "income"
                            } else {
                                "expense"
                            }
                        }
                    }
                }

                if (amount == null || amount <= 0.0) {
                    errorCount++
                    continue
                }

                // Category
                var catId: Long? = null
                val catCol = mapping["category"]
                if (catCol != null && rowDict[catCol]?.isNotEmpty() == true) {
                    val rawCat = rowDict[catCol]!!.lowercase().trim()
                    catId = catByName[rawCat]?.id
                }

                if (catId == null && type == "expense") {
                    val lowerDesc = desc.lowercase()
                    catId = when {
                        lowerDesc.containsAny("swiggy", "zomato", "restaurant", "cafe", "food", "mcdonald") ->
                            catByName["dining out"]?.id ?: catByName["groceries"]?.id
                        lowerDesc.containsAny("uber", "ola", "metro", "fuel", "petrol", "transit") ->
                            catByName["transportation"]?.id
                        lowerDesc.containsAny("amazon", "flipkart", "shopping", "clothes") ->
                            catByName["personal"]?.id ?: catByName["entertainment"]?.id
                        lowerDesc.containsAny("netflix", "spotify", "movie", "cinema", "prime") ->
                            catByName["entertainment"]?.id
                        lowerDesc.containsAny("hospital", "doctor", "pharmacy", "medicine", "health") ->
                            catByName["healthcare"]?.id
                        else -> defaultCategoryId ?: categories.firstOrNull()?.id
                    }
                }

                parsedList.add(
                    TransactionEntity(
                        date = parsedDate,
                        amount = amount,
                        type = type,
                        categoryId = if (type == "expense") catId else null,
                        description = desc.ifBlank { if (type == "income") "Income" else "Expense" },
                        fundingSource = "regular",
                        status = "confirmed"
                    )
                )
            }
        }

        return CsvParseResult(
            transactions = parsedList,
            totalRows = parsedList.size + errorCount,
            validRows = parsedList.size,
            errorCount = errorCount
        )
    }

    private fun detectColumns(headers: List<String>): Map<String, String> {
        val mapping = mutableMapOf<String, String>()
        val dateCandidates = listOf("date", "txn_date", "transaction_date", "value_date", "posting_date")
        val descCandidates = listOf("description", "desc", "narration", "remarks", "particulars", "payee", "paid_to", "merchant")
        val amtCandidates = listOf("amount", "amt", "transaction_amount", "net_amount", "total")
        val debitCandidates = listOf("debit", "withdrawal", "dr", "debit_amount", "spent", "paid_out")
        val creditCandidates = listOf("credit", "deposit", "cr", "credit_amount", "received", "paid_in")
        val typeCandidates = listOf("type", "txn_type", "transaction_type", "dr_cr")
        val catCandidates = listOf("category", "category_name", "tag")

        for (h in headers) {
            val norm = h.trim().lowercase().replace(" ", "_").replace("-", "_")
            if (!mapping.containsKey("date") && dateCandidates.any { norm.contains(it) }) mapping["date"] = h
            if (!mapping.containsKey("description") && descCandidates.any { norm.contains(it) }) mapping["description"] = h
            if (!mapping.containsKey("debit") && debitCandidates.any { norm.contains(it) }) mapping["debit"] = h
            if (!mapping.containsKey("credit") && creditCandidates.any { norm.contains(it) }) mapping["credit"] = h
            if (!mapping.containsKey("amount") && amtCandidates.any { norm.contains(it) }) mapping["amount"] = h
            if (!mapping.containsKey("type") && typeCandidates.any { norm.contains(it) }) mapping["type"] = h
            if (!mapping.containsKey("category") && catCandidates.any { norm.contains(it) }) mapping["category"] = h
        }
        return mapping
    }

    private fun parseAmountString(raw: String?): Double? {
        if (raw.isNullOrBlank()) return null
        val cleaned = raw.replace(Regex("[^0-9.-]"), "")
        return cleaned.toDoubleOrNull()
    }

    private fun parseDateString(raw: String): String? {
        val trimmed = raw.trim().split(" ").firstOrNull() ?: return null
        // YYYY-MM-DD
        if (trimmed.matches(Regex("^\\d{4}-\\d{2}-\\d{2}$"))) return trimmed

        val patterns = listOf(
            "dd-MM-yyyy", "dd/MM/yyyy", "dd.MM.yyyy",
            "d-M-yyyy", "d/M/yyyy",
            "dd-MMM-yyyy", "dd/MMM/yyyy", "dd MMM yyyy",
            "yyyy/MM/dd", "MM/dd/yyyy"
        )
        for (pattern in patterns) {
            try {
                val dtf = DateTimeFormatter.ofPattern(pattern, Locale.US)
                val parsed = LocalDate.parse(trimmed, dtf)
                return parsed.toString()
            } catch (e: Exception) {
                // Continue trying patterns
            }
        }
        return null
    }

    private fun splitCsvLine(line: String): List<String> {
        val tokens = mutableListOf<String>()
        var inQuotes = false
        val sb = StringBuilder()
        for (c in line) {
            when {
                c == '\"' -> inQuotes = !inQuotes
                c == ',' && !inQuotes -> {
                    tokens.add(sb.toString().trim())
                    sb.clear()
                }
                else -> sb.append(c)
            }
        }
        tokens.add(sb.toString().trim())
        return tokens
    }

    private fun String.containsAny(vararg keywords: String): Boolean {
        return keywords.any { this.contains(it) }
    }
}
