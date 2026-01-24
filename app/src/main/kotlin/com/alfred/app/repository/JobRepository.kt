package com.alfred.app.repository

import com.alfred.app.entity.Job
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.stereotype.Repository
import java.util.UUID

@Repository
interface JobRepository : JpaRepository<Job, UUID> {
    fun findByUserIdOrderByCreatedAtDesc(userId: UUID): List<Job>
}
