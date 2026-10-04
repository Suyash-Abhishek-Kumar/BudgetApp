package com.budgetapp.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "categories")
data class CategoryEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val name: String,
    @ColumnInfo(name = "soft_limit")
    val softLimit: Double,
    @ColumnInfo(name = "hard_limit")
    val hardLimit: Double,
    @ColumnInfo(name = "created_at")
    val createdAt: String
)

