package com.alfred.app.entity

import jakarta.persistence.*
import org.hibernate.annotations.Immutable
import java.time.LocalDateTime
import java.util.UUID

@Entity
@Table(name = "jobs")
@Immutable
class Job(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    val id: UUID? = null,

    @Column(name = "user_id", nullable = false)
    val userId: UUID,

    @Column(nullable = false, columnDefinition = "TEXT")
    val prompt: String,

    @Column(columnDefinition = "TEXT")
    val result: String? = null,

    @Column(length = 50)
    val status: String = "pending",

    @Column(name = "created_at", nullable = false, updatable = false)
    val createdAt: LocalDateTime,

    @Column(name = "completed_at")
    val completedAt: LocalDateTime? = null
)
