package com.alfred.app.config

import io.jsonwebtoken.security.Keys
import org.springframework.boot.context.properties.ConfigurationProperties
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import javax.crypto.SecretKey

@ConfigurationProperties(prefix = "app.jwt")
data class JwtProperties(
    val secret: String,
    val expirationMs: Long,
    val issuer: String
)

@Configuration
class JwtConfig(private val jwtProperties: JwtProperties) {

    @Bean
    fun secretKey(): SecretKey {
        return Keys.hmacShaKeyFor(jwtProperties.secret.toByteArray())
    }
}
