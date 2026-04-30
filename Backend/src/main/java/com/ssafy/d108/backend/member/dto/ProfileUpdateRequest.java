package com.ssafy.d108.backend.member.dto;

import com.ssafy.d108.backend.entity.enums.*;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDate;
import java.util.Set;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class ProfileUpdateRequest {

    @JsonProperty("gender")
    private Gender gender;

    @JsonProperty("birth_date")
    @JsonFormat(pattern = "yyyy-MM-dd")
    private LocalDate birthDate;

    @JsonProperty("height")
    private Float height;

    @JsonProperty("weight")
    private Float weight;

    @JsonProperty("top_size")
    private TopSize topSize;

    @JsonProperty("bottom_size")
    private BottomSize bottomSize;

    @JsonProperty("shoe_size")
    private ShoeSize shoeSize;

    @JsonProperty("allergies")
    private Set<Allergy> allergies;

    @JsonProperty("etc_allergy")
    private String etcAllergy;
}
