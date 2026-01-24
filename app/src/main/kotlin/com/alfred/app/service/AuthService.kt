package com.alfred.app.service

import com.alfred.app.config.JwtProperties
import com.alfred.app.dto.AuthResponse
import com.alfred.app.dto.LoginRequest
import com.alfred.app.dto.RegisterRequest
import com.alfred.app.entity.User
import com.alfred.app.repository.UserRepository
import org.springframework.security.authentication.BadCredentialsException
import org.springframework.security.crypto.password.PasswordEncoder
import org.springframework.stereotype.Service

@Service
class AuthService(
    private val userRepository: UserRepository,
    private val passwordEncoder: PasswordEncoder,
    private val jwtService: JwtService,
    private val jwtProperties: JwtProperties
) {

    fun register(request: RegisterRequest): AuthResponse {
        if (userRepository.existsByEmail(request.email)) {
            throw IllegalArgumentException("Email already registered")
        }

        val encodedPassword = passwordEncoder.encode(request.password)!!
        val user = User(
            email = request.email,
            password = encodedPassword
        )

        val savedUser = userRepository.save(user)
        val userId = savedUser.id ?: throw IllegalStateException("User ID is null after save")
        val token = jwtService.generateToken(userId, savedUser.email)

        return AuthResponse(
            token = token,
            userId = userId,
            email = savedUser.email,
            expiresIn = jwtProperties.expirationMs / 1000
        )
    }

    fun login(request: LoginRequest): AuthResponse {
        val user = userRepository.findByEmail(request.email)
            ?: throw BadCredentialsException("Invalid email or password")

        if (!passwordEncoder.matches(request.password, user.password)) {
            throw BadCredentialsException("Invalid email or password")
        }

        val userId = user.id ?: throw IllegalStateException("User ID is null")
        val token = jwtService.generateToken(userId, user.email)

        return AuthResponse(
            token = token,
            userId = userId,
            email = user.email,
            expiresIn = jwtProperties.expirationMs / 1000
        )
    }
}
