package com.alfred.app.dto

import java.util.UUID

data class AuthResponse(
    val token: String,
    val userId: UUID,
    val email: String,
    val expiresIn: Long
)
