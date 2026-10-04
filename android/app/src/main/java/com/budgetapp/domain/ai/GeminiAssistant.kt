package com.budgetapp.domain.ai

import com.google.ai.client.generativeai.GenerativeModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class GeminiAssistant(
    private val apiKey: String,
    private val modelName: String = "gemini-1.5-flash"
) {

    companion object {
        val DEFAULT_MODELS = listOf(
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro"
        )
        const val DEFAULT_MODEL = "gemini-1.5-flash"

        /**
         * Dynamically queries the Google Gemini API using the provided API key
         * to discover all currently active, supported chat/content generation models.
         * Prioritizes flash and pro text-generation models and filters out non-chat models.
         * Falls back to curated DEFAULT_MODELS on failure or offline conditions.
         */
        suspend fun fetchAvailableModels(apiKey: String): List<String> = withContext(Dispatchers.IO) {
            val key = apiKey.trim()
            if (key.isBlank()) return@withContext DEFAULT_MODELS

            try {
                val url = URL("https://generativelanguage.googleapis.com/v1beta/models?key=$key")
                val connection = (url.openConnection() as HttpURLConnection).apply {
                    requestMethod = "GET"
                    connectTimeout = 8000
                    readTimeout = 8000
                    setRequestProperty("Accept", "application/json")
                }

                if (connection.responseCode == HttpURLConnection.HTTP_OK) {
                    val responseBody = connection.inputStream.bufferedReader().use { it.readText() }
                    val json = JSONObject(responseBody)
                    val modelsArray = json.optJSONArray("models")

                    if (modelsArray != null) {
                        val discovered = mutableListOf<String>()
                        for (i in 0 until modelsArray.length()) {
                            val modelObj = modelsArray.optJSONObject(i) ?: continue
                            val name = modelObj.optString("name", "") // e.g., "models/gemini-1.5-flash"
                            val cleanId = name.substringAfterLast("/")

                            // Verify it supports generateContent
                            val supportedMethods = modelObj.optJSONArray("supportedGenerationMethods")
                            var supportsGenerate = false
                            if (supportedMethods != null) {
                                for (j in 0 until supportedMethods.length()) {
                                    if (supportedMethods.optString(j) == "generateContent") {
                                        supportsGenerate = true
                                        break
                                    }
                                }
                            }

                            if (!cleanId.startsWith("gemini", ignoreCase = true)) continue
                            if (!supportsGenerate) continue

                            val lower = cleanId.lowercase()
                            val isExcluded = listOf("embedding", "imagen", "aqa", "realtime", "tts", "learnlm").any { lower.contains(it) }
                            if (!isExcluded && !discovered.contains(cleanId)) {
                                discovered.add(cleanId)
                            }
                        }

                        if (discovered.isNotEmpty()) {
                            // Sort flash first, then pro, then newer versions
                            discovered.sortWith(
                                compareBy<String> { if (it.contains("flash", ignoreCase = true)) 0 else 1 }
                                    .thenByDescending { it }
                            )
                            return@withContext discovered
                        }
                    }
                }
            } catch (e: Exception) {
                // Network or API failure, fallback gracefully
            }
            return@withContext DEFAULT_MODELS
        }
    }

    fun streamChatResponse(prompt: String, contextSystemPrompt: String): Flow<String> = flow {
        if (apiKey.isBlank()) {
            emit("⚠️ Please set your Google Gemini API Key in the AI Assistant settings to chat.")
            return@flow
        }

        try {
            val generativeModel = GenerativeModel(
                modelName = modelName.ifBlank { DEFAULT_MODEL },
                apiKey = apiKey,
                systemInstruction = com.google.ai.client.generativeai.type.content {
                    text(contextSystemPrompt)
                }
            )

            val response = generativeModel.generateContent(prompt)
            emit(response.text ?: "No response received.")
        } catch (e: Exception) {
            emit("Error connecting to Gemini: ${e.localizedMessage ?: "Unknown error"}")
        }
    }
}
