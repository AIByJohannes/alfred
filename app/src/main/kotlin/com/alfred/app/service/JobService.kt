package com.alfred.app.service

import com.alfred.app.dto.JobDto
import com.alfred.app.dto.JobHistoryResponse
import com.alfred.app.repository.JobRepository
import org.springframework.stereotype.Service
import java.util.UUID

@Service
class JobService(
    private val jobRepository: JobRepository
) {

    fun getJobHistory(userId: UUID): JobHistoryResponse {
        val jobs = jobRepository.findByUserIdOrderByCreatedAtDesc(userId)

        val jobDtos = jobs.map { job ->
            JobDto(
                id = job.id ?: throw IllegalStateException("Job ID is null"),
                prompt = job.prompt,
                result = job.result,
                status = job.status,
                createdAt = job.createdAt,
                completedAt = job.completedAt
            )
        }

        return JobHistoryResponse(
            jobs = jobDtos,
            total = jobDtos.size
        )
    }
}
