package com.alfred.app.service

import com.alfred.app.config.JwtProperties
import io.jsonwebtoken.Claims
import io.jsonwebtoken.Jwts
import org.springframework.stereotype.Service
import java.util.*
import javax.crypto.SecretKey

@Service
class JwtService(
    private val jwtProperties: JwtProperties,
    private val secretKey: SecretKey
) {

    fun generateToken(userId: UUID, email: String): String {
        val now = Date()
        val expiryDate = Date(now.time + jwtProperties.expirationMs)

        return Jwts.builder()
            .subject(userId.toString())
            .claim("email", email)
            .issuer(jwtProperties.issuer)
            .issuedAt(now)
            .expiration(expiryDate)
            .signWith(secretKey)
            .compact()
    }

    fun validateToken(token: String): Boolean {
        return try {
            Jwts.parser()
                .verifyWith(secretKey)
                .build()
                .parseSignedClaims(token)
            true
        } catch (e: Exception) {
            false
        }
    }

    fun getUserIdFromToken(token: String): UUID {
        val claims = getClaims(token)
        return UUID.fromString(claims.subject)
    }

    fun getEmailFromToken(token: String): String {
        val claims = getClaims(token)
        return claims["email"] as String
    }

    private fun getClaims(token: String): Claims {
        return Jwts.parser()
            .verifyWith(secretKey)
            .build()
            .parseSignedClaims(token)
            .payload
    }
}
