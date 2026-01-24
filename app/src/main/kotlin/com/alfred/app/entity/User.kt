package com.alfred.app.entity

import jakarta.persistence.*
import java.time.LocalDateTime
import java.util.UUID

@Entity
@Table(name = "users")
class User(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    val id: UUID? = null,

    @Column(unique = true, nullable = false)
    val email: String = "",

    @Column(nullable = false)
    val password: String = "",

    @Column(name = "created_at", nullable = false, updatable = false)
    val createdAt: LocalDateTime = LocalDateTime.now(),

    @Column(name = "updated_at", nullable = false)
    val updatedAt: LocalDateTime = LocalDateTime.now()
) {
    constructor(email: String, password: String) : this(
        id = null,
        email = email,
        password = password,
        createdAt = LocalDateTime.now(),
        updatedAt = LocalDateTime.now()
    )
}
