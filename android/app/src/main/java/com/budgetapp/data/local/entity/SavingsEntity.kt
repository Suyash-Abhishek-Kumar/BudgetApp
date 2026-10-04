package com.budgetapp.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "savings",
    indices = [
        Index(value = ["month"], unique = true)
    ]
)
data class SavingsEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val month: String, // 'YYYY-MM'
    @ColumnInfo(name = "rollover_amount")
    val rolloverAmount: Double,
    @ColumnInfo(name = "emergency_fund_delta")
    val emergencyFundDelta: Double = 0.0
)

