package com.budgetapp.domain.ai

import com.google.ai.client.generativeai.GenerativeModel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow

class GeminiAssistant(
    private val apiKey: String,
    private val modelName: String = "gemini-1.5-flash"
) {

    fun streamChatResponse(prompt: String, contextSystemPrompt: String): Flow<String> = flow {
        if (apiKey.isBlank()) {
            emit("⚠️ Please set your Google Gemini API Key in the AI Assistant settings to chat.")
            return@flow
        }

        try {
            val generativeModel = GenerativeModel(
                modelName = modelName.ifBlank { "gemini-1.5-flash" },
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
