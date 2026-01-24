package com.alfred.app.dto

import java.time.LocalDateTime
import java.util.UUID

data class JobDto(
    val id: UUID,
    val prompt: String,
    val result: String?,
    val status: String,
    val createdAt: LocalDateTime,
    val completedAt: LocalDateTime?
)

data class JobHistoryResponse(
    val jobs: List<JobDto>,
    val total: Int
)
