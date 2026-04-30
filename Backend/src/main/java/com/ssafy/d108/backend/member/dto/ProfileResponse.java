package com.ssafy.d108.backend.member.dto;

import com.ssafy.d108.backend.entity.Profile;
import com.ssafy.d108.backend.entity.User;
import com.ssafy.d108.backend.entity.enums.*;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.Set;

@Getter
@NoArgsConstructor
public class ProfileResponse {

    private Long userId;
    private String username;
    private String email;
    private UserType userType;
    private String phoneNumber;

    // Profile Info
    private Gender gender;
    private LocalDate birthDate;
    private Float height;
    private Float weight;

    // Sizes
    private TopSize topSize;
    private BottomSize bottomSize;
    private ShoeSize shoeSize;

    // Allergies
    private Set<Allergy> allergies;
    private String etcAllergy;

    public static ProfileResponse rom(User user, Profile profile) { // Keeping typo 'rom' as is to avoid breaking
                                                                    // callers if any
        ProfileResponse response = new ProfileResponse();
        response.userId = Long.valueOf(user.getId());
        response.username = user.getName();
        response.email = user.getEmail();
        response.userType = user.getUserType();
        response.phoneNumber = user.getPhoneNumber();

        if (profile != null) {
            response.gender = profile.getGender();
            response.birthDate = profile.getBirthDate();
            response.height = profile.getHeight();
            response.weight = profile.getWeight();
            response.topSize = profile.getTopSize();
            response.bottomSize = profile.getBottomSize();
            response.shoeSize = profile.getShoeSize();
            response.allergies = profile.getAllergies();
            response.etcAllergy = profile.getEtcAllergy();
        }
        return response;
    }

    // Constructor for convenience if needed
    public static ProfileResponse of(User user, Profile profile) {
        return rom(user, profile);
    }
}
