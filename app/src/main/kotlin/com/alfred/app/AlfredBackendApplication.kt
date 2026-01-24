package com.alfred.app

import com.alfred.app.config.JwtProperties
import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.context.properties.EnableConfigurationProperties
import org.springframework.boot.runApplication

@SpringBootApplication
@EnableConfigurationProperties(JwtProperties::class)
class AlfredBackendApplication

fun main(args: Array<String>) {
	runApplication<AlfredBackendApplication>(*args)
}
