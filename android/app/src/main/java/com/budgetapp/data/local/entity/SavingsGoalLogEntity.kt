package com.budgetapp.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "savings_goal_logs",
    foreignKeys = [
        ForeignKey(
            entity = SavingsGoalEntity::class,
            parentColumns = ["id"],
            childColumns = ["goal_id"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [
        Index("goal_id"),
        Index("date")
    ]
)
data class SavingsGoalLogEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    @ColumnInfo(name = "goal_id")
    val goalId: Long,
    val date: String, // 'YYYY-MM-DD'
    val amount: Double, // positive = deposit, negative = withdrawal
    val type: String, // 'deposit', 'withdrawal'
    val note: String? = null,
    @ColumnInfo(name = "created_at")
    val createdAt: String
)
