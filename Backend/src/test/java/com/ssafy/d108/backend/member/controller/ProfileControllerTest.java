package com.ssafy.d108.backend.member.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.d108.backend.entity.enums.*;
import com.ssafy.d108.backend.member.dto.ProfileResponse;
import com.ssafy.d108.backend.member.dto.ProfileUpdateRequest;
import com.ssafy.d108.backend.member.service.ProfileService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Set;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.mock;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultHandlers.print;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = ProfileController.class)
@AutoConfigureMockMvc(addFilters = false) // Disable security filters for simple testing
class ProfileControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ProfileService profileService;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    @DisplayName("내 프로필 수정 테스트 - 성공")
    void updateMyProfile() throws Exception {
        // Given
        Integer userId = 1;

        // Mock Request Body
        ProfileUpdateRequest request = new ProfileUpdateRequest();
        request.setHeight(180.5f);
        request.setTopSize(TopSize.L);
        request.setAllergies(Set.of(Allergy.NUTS));
        request.setEtcAllergy("Peach");

        // Mock Response - ProfileResponse is now immutable, use mock
        ProfileResponse response = mock(ProfileResponse.class);
        given(response.getUserId()).willReturn(Long.valueOf(userId));
        given(response.getHeight()).willReturn(180.5f);
        given(response.getEtcAllergy()).willReturn("Peach");

        given(profileService.updateProfile(eq(userId), any(ProfileUpdateRequest.class))).willReturn(response);

        // Security Context Setup
        UsernamePasswordAuthenticationToken auth = new UsernamePasswordAuthenticationToken("customUser", "password");
        auth.setDetails(userId); // Important: details must be Integer for SecurityUtil.getCurrentUserId()

        // When & Then
        mockMvc.perform(put("/members/profile")
                .with(request1 -> {
                    // Set SecurityContext manually for SecurityUtil to work
                    org.springframework.security.core.context.SecurityContextHolder.getContext()
                            .setAuthentication(auth);
                    return request1;
                })
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request))
                .with(csrf()))
                .andDo(print())
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.etcAllergy").value("Peach"));
    }
}
