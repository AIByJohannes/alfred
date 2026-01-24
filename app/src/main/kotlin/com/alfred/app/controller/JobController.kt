package com.alfred.app.controller

import com.alfred.app.dto.JobHistoryResponse
import com.alfred.app.repository.UserRepository
import com.alfred.app.service.JobService
import org.springframework.http.ResponseEntity
import org.springframework.security.core.Authentication
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api/jobs")
class JobController(
    private val jobService: JobService,
    private val userRepository: UserRepository
) {

    @GetMapping("/history")
    fun getJobHistory(authentication: Authentication): ResponseEntity<JobHistoryResponse> {
        // Extract email from security context (set by JWT filter)
        val email = authentication.name

        // Lookup user to get UUID
        val user = userRepository.findByEmail(email)
            ?: throw IllegalStateException("Authenticated user not found")

        val userId = user.id ?: throw IllegalStateException("User ID is null")

        // Get job history
        val response = jobService.getJobHistory(userId)
        return ResponseEntity.ok(response)
    }
}
