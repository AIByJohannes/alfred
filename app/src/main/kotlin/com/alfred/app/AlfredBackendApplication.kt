package com.alfred.app

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class AlfredBackendApplication

fun main(args: Array<String>) {
	runApplication<AlfredBackendApplication>(*args)
}
