package com.ssafy.d108.backend.auth.repository;

import com.ssafy.d108.backend.entity.WelfareCard;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.Optional;

/**
 * WelfareCard Repository
 */
@Repository
public interface WelfareCardRepository extends JpaRepository<WelfareCard, Integer> {

    Optional<WelfareCard> findByUserId(Integer userId);

    boolean existsByUserId(Integer userId);

    Optional<WelfareCard> findByCardNumberAndCardCompanyAndIssueDateAndExpirationDateAndCvc(
            String cardNumber, String cardCompany, LocalDate issueDate, String expirationDate, String cvc);

    Optional<WelfareCard> findByCardNumberAndCardCompanyAndExpirationDateAndCvc(
            String cardNumber, String cardCompany, String expirationDate, String cvc);

    @Modifying
    @Query("DELETE FROM WelfareCard w WHERE w.user.id = :userId")
    void deleteByUserId(@Param("userId") Integer userId);
}
