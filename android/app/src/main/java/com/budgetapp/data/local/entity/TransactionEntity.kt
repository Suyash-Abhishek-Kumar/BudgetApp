package com.budgetapp.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "transactions",
    foreignKeys = [
        ForeignKey(
            entity = CategoryEntity::class,
            parentColumns = ["id"],
            childColumns = ["category_id"],
            onDelete = ForeignKey.SET_NULL
        ),
        ForeignKey(
            entity = RecurringTransactionEntity::class,
            parentColumns = ["id"],
            childColumns = ["recurring_id"],
            onDelete = ForeignKey.SET_NULL
        )
    ],
    indices = [
        Index("date"),
        Index("category_id"),
        Index("status"),
        Index("split_group_id")
    ]
)
data class TransactionEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val date: String, // 'YYYY-MM-DD'
    val amount: Double,
    val type: String, // 'expense' or 'income'
    @ColumnInfo(name = "category_id")
    val categoryId: Long? = null,
    val description: String? = null,
    @ColumnInfo(name = "funding_source")
    val fundingSource: String = "regular", // 'regular', 'savings', 'emergency_fund'
    @ColumnInfo(name = "recurring_id")
    val recurringId: Long? = null,
    val status: String = "confirmed", // 'confirmed', 'pending_approval'
    @ColumnInfo(name = "split_group_id")
    val splitGroupId: String? = null
)
