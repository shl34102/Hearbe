package com.ssafy.d108.backend.member.service;

import com.ssafy.d108.backend.entity.Profile;
import com.ssafy.d108.backend.entity.User;
import com.ssafy.d108.backend.member.dto.ProfileResponse;
import com.ssafy.d108.backend.member.dto.ProfileUpdateRequest;
import com.ssafy.d108.backend.member.repository.ProfileRepository;
import com.ssafy.d108.backend.auth.repository.UserRepository;
import com.ssafy.d108.backend.global.exception.UserNotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ProfileService {

    private final ProfileRepository profileRepository;
    private final UserRepository userRepository;

    /**
     * 내 정보 조회
     * 프로필이 없으면 빈 프로필 생성 후 반환 (또는 null 반환)
     */
    @Transactional
    public ProfileResponse getProfile(Integer userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new UserNotFoundException("사용자를 찾을 수 없습니다."));

        Profile profile = profileRepository.findByUser(user)
                .orElseGet(() -> createEmptyProfile(user));

        return ProfileResponse.of(user, profile);
    }

    @Transactional
    public Profile createEmptyProfile(User user) {
        Profile profile = new Profile();
        profile.setUser(user);
        return profileRepository.save(profile);
    }

    /**
     * 내 정보 수정
     */
    @Transactional
    public ProfileResponse updateProfile(Integer userId, ProfileUpdateRequest request) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new UserNotFoundException("사용자를 찾을 수 없습니다."));

        Profile profile = profileRepository.findByUser(user)
                .orElseGet(() -> createEmptyProfile(user));

        // Update fields
        if (request.getGender() != null)
            profile.setGender(request.getGender());
        if (request.getBirthDate() != null)
            profile.setBirthDate(request.getBirthDate());
        if (request.getHeight() != null)
            profile.setHeight(request.getHeight());
        if (request.getWeight() != null)
            profile.setWeight(request.getWeight());
        if (request.getTopSize() != null)
            profile.setTopSize(request.getTopSize());
        if (request.getBottomSize() != null)
            profile.setBottomSize(request.getBottomSize());
        if (request.getShoeSize() != null)
            profile.setShoeSize(request.getShoeSize());

        // Update Allergies
        if (request.getAllergies() != null) {
            profile.getAllergies().clear();
            profile.getAllergies().addAll(request.getAllergies());
        }

        // Update Etc Allergy
        if (request.getEtcAllergy() != null) {
            profile.setEtcAllergy(request.getEtcAllergy());
        }

        return ProfileResponse.of(user, profile);
    }
}
