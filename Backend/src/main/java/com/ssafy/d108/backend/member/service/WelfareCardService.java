package com.ssafy.d108.backend.member.service;

import com.ssafy.d108.backend.auth.dto.WelfareCardRequest;
import com.ssafy.d108.backend.auth.dto.WelfareCardResponse;
import com.ssafy.d108.backend.auth.repository.UserRepository;
import com.ssafy.d108.backend.auth.repository.WelfareCardRepository;
import com.ssafy.d108.backend.entity.User;
import com.ssafy.d108.backend.entity.WelfareCard;
import com.ssafy.d108.backend.global.exception.UserNotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;

/**
 * 복지카드 관리 서비스
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class WelfareCardService {

    private final UserRepository userRepository;
    private final WelfareCardRepository welfareCardRepository;
    private final com.ssafy.d108.backend.global.util.AESUtil aesUtil;

    /**
     * 복지카드 등록
     */
    @Transactional
    public WelfareCardResponse registerWelfareCard(Integer userId, WelfareCardRequest request) {
        // 사용자 조회
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new UserNotFoundException("사용자를 찾을 수 없습니다."));

        // 유효기간 검증
        validateCard(request);

        // 이미 존재하는지 확인
        if (welfareCardRepository.existsByUserId(userId)) {
            throw new IllegalArgumentException("이미 등록된 복지카드가 있습니다. 수정을 이용해주세요.");
        }

        WelfareCard welfareCard = new WelfareCard();
        welfareCard.setUser(user);
        welfareCard.setCardCompany(request.getCardCompany());
        // 숫자만 저장 -> 암호화
        String rawCardNumber = request.getCardNumber().replaceAll("[^0-9]", "");
        welfareCard.setCardNumber(aesUtil.encrypt(rawCardNumber));

        welfareCard.setIssueDate(request.getIssueDate());
        welfareCard.setExpirationDate(request.getExpirationDate());

        // CVC 암호화
        welfareCard.setCvc(aesUtil.encrypt(request.getCvc()));

        WelfareCard saved = welfareCardRepository.save(welfareCard);
        return toResponse(userId, saved);
    }

    /**
     * 복지카드 수정
     */
    @Transactional
    public WelfareCardResponse updateWelfareCard(Integer userId, WelfareCardRequest request) {
        WelfareCard welfareCard = welfareCardRepository.findByUserId(userId)
                .orElseThrow(() -> new IllegalArgumentException("등록된 복지카드가 없습니다. 등록을 먼저 해주세요."));

        // 유효기간 검증
        validateCard(request);

        // 정보 업데이트
        welfareCard.setCardCompany(request.getCardCompany());
        // 숫자만 저장 -> 암호화
        String rawCardNumber = request.getCardNumber().replaceAll("[^0-9]", "");
        welfareCard.setCardNumber(aesUtil.encrypt(rawCardNumber));

        welfareCard.setIssueDate(request.getIssueDate());
        welfareCard.setExpirationDate(request.getExpirationDate());
        // CVC 암호화
        welfareCard.setCvc(aesUtil.encrypt(request.getCvc()));

        return toResponse(userId, welfareCard);
    }

    /**
     * 복지카드 삭제
     */
    @Transactional
    public void deleteWelfareCard(Integer userId) {
        if (!welfareCardRepository.existsByUserId(userId)) {
            throw new IllegalArgumentException("삭제할 복지카드가 없습니다.");
        }
        welfareCardRepository.deleteByUserId(userId);
    }

    // MM/YY 형식은 날짜 비교 불가능하므로 패턴 검증만 수행 (Validation 어노테이션에서 처리)
    private void validateCard(WelfareCardRequest request) {
        // Pattern validation은 @Pattern 어노테이션에서 자동 처리됨
    }

    private WelfareCardResponse toResponse(Integer userId, WelfareCard card) {
        // 복호화하여 반환 (응답에는 평문 카드번호 제공, CVC는 제외)
        String decryptedCardNumber = aesUtil.decrypt(card.getCardNumber());

        return new WelfareCardResponse(
                card.getId(),
                userId,
                card.getCardCompany(),
                decryptedCardNumber,
                card.getIssueDate(),
                card.getExpirationDate(),
                card.getCvc() != null,
                true,
                card.getCreatedAt(),
                card.getUpdatedAt());
    }

    /**
     * 복지카드 조회
     */
    public WelfareCardResponse getWelfareCard(Integer userId) {
        // 사용자 존재 확인
        if (!userRepository.existsById(userId)) {
            throw new UserNotFoundException("사용자를 찾을 수 없습니다.");
        }

        Optional<WelfareCard> welfareCard = welfareCardRepository.findByUserId(userId);

        if (welfareCard.isPresent()) {
            WelfareCard card = welfareCard.get();
            // 복호화
            String decryptedCardNumber = aesUtil.decrypt(card.getCardNumber());

            return new WelfareCardResponse(
                    card.getId(),
                    userId,
                    card.getCardCompany(),
                    decryptedCardNumber,
                    card.getIssueDate(),
                    card.getExpirationDate(),
                    card.getCvc() != null, // CVC 존재 여부만 반환
                    true,
                    card.getCreatedAt(),
                    card.getUpdatedAt());
        } else {
            // 복지카드 없음
            return new WelfareCardResponse(
                    null,
                    userId,
                    null,
                    null,
                    null,
                    null,
                    false,
                    false,
                    null,
                    null);
        }
    }

}
