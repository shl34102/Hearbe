package com.ssafy.d108.backend.auth.repository;

import com.ssafy.d108.backend.entity.SharingSessionLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface SharingSessionLogRepository extends JpaRepository<SharingSessionLog, Integer> {

    @Modifying
    @Query("DELETE FROM SharingSessionLog s WHERE s.hostUser.id = :userId")
    void deleteAllByHostUserId(@Param("userId") Integer userId);
}
