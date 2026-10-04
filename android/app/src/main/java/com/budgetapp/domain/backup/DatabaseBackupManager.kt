package com.budgetapp.domain.backup

import android.content.Context
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class BackupFileInfo(
    val file: File,
    val filename: String,
    val sizeKb: Double,
    val createdAt: String
)

object DatabaseBackupManager {

    fun getBackupDirectory(context: Context): File {
        val backupDir = File(context.filesDir, "backups")
        if (!backupDir.exists()) {
            backupDir.mkdirs()
        }
        return backupDir
    }

    fun createBackup(context: Context): BackupFileInfo {
        val dbFile = context.getDatabasePath("budget.db")
        if (!dbFile.exists()) {
            throw IllegalStateException("Database file does not exist yet.")
        }

        val backupDir = getBackupDirectory(context)
        val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val backupFile = File(backupDir, "budget_backup_$timestamp.db")

        // Atomic file copy
        FileInputStream(dbFile).use { input ->
            FileOutputStream(backupFile).use { output ->
                input.copyTo(output)
            }
        }

        val sizeKb = kotlin.math.round((backupFile.length() / 1024.0) * 10.0) / 10.0
        val createdStr = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(Date(backupFile.lastModified()))

        return BackupFileInfo(backupFile, backupFile.name, sizeKb, createdStr)
    }

    fun listBackups(context: Context): List<BackupFileInfo> {
        val backupDir = getBackupDirectory(context)
        val files = backupDir.listFiles { _, name -> name.startsWith("budget_backup_") && name.endsWith(".db") } ?: return emptyList()

        return files.map { f ->
            val sizeKb = kotlin.math.round((f.length() / 1024.0) * 10.0) / 10.0
            val createdStr = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(Date(f.lastModified()))
            BackupFileInfo(f, f.name, sizeKb, createdStr)
        }.sortedByDescending { it.file.lastModified() }
    }

    fun restoreBackup(context: Context, backupFile: File) {
        val dbFile = context.getDatabasePath("budget.db")
        if (!backupFile.exists()) {
            throw IllegalArgumentException("Backup file does not exist.")
        }

        FileInputStream(backupFile).use { input ->
            FileOutputStream(dbFile).use { output ->
                input.copyTo(output)
            }
        }
    }

    fun deleteBackup(backupFile: File): Boolean {
        return backupFile.delete()
    }
}
