package com.budgetapp.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "recurring_transactions",
    foreignKeys = [
        ForeignKey(
            entity = CategoryEntity::class,
            parentColumns = ["id"],
            childColumns = ["category_id"],
            onDelete = ForeignKey.SET_NULL
        )
    ],
    indices = [
        Index("category_id")
    ]
)
data class RecurringTransactionEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    @ColumnInfo(name = "category_id")
    val categoryId: Long? = null,
    val amount: Double,
    val description: String? = null,
    val type: String, // 'expense' or 'income'
    val frequency: String, // 'daily', 'monthly', 'yearly', 'custom'
    @ColumnInfo(name = "interval_days")
    val intervalDays: Int? = null,
    @ColumnInfo(name = "next_due_date")
    val nextDueDate: String, // 'YYYY-MM-DD'
    val active: Int = 1,
    @ColumnInfo(name = "created_at")
    val createdAt: String
)

