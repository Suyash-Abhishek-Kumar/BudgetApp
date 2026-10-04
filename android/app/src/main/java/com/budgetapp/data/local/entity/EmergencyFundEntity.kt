package com.budgetapp.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "emergency_fund")
data class EmergencyFundEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val balance: Double = 0.0,
    @ColumnInfo(name = "last_updated")
    val lastUpdated: String
)

@Entity(tableName = "emergency_fund_log")
data class EmergencyFundLogEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val date: String,
    val amount: Double,
    val source: String, // 'monthly_rollover', 'manual'
    val note: String? = null
)

