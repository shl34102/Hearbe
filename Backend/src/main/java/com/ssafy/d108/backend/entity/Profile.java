package com.ssafy.d108.backend.entity;

import com.ssafy.d108.backend.entity.enums.Allergy;
import com.ssafy.d108.backend.entity.enums.BottomSize;
import com.ssafy.d108.backend.entity.enums.Gender;
import com.ssafy.d108.backend.entity.enums.ShoeSize;
import com.ssafy.d108.backend.entity.enums.TopSize;

import java.time.LocalDate;
import java.util.HashSet;
import java.util.Set;
import jakarta.persistence.CollectionTable;
import jakarta.persistence.ElementCollection;
import java.time.LocalDateTime;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.UpdateTimestamp;

@Entity
@Table(name = "profiles")
@Getter
@Setter
@NoArgsConstructor
public class Profile {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Integer id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false, unique = true)
    private User user;

    @Enumerated(EnumType.STRING)
    @Column(name = "gender", length = 1)
    private Gender gender;

    @Column(name = "height")
    private Float height;

    @Column(name = "weight")
    private Float weight;

    @Enumerated(EnumType.STRING)
    @Column(name = "top_size")
    private TopSize topSize;

    @Enumerated(EnumType.STRING)
    @Column(name = "bottom_size")
    private BottomSize bottomSize;

    @Enumerated(EnumType.STRING)
    @Column(name = "shoe_size")
    private ShoeSize shoeSize;

    @ElementCollection(targetClass = Allergy.class, fetch = FetchType.EAGER)
    @CollectionTable(name = "profile_allergies", joinColumns = @JoinColumn(name = "profile_id"))
    @Enumerated(EnumType.STRING)
    @Column(name = "allergy")
    private Set<Allergy> allergies = new HashSet<>();

    @Column(name = "etc_allergy")
    private String etcAllergy;

    @Column(name = "birth_date")
    private LocalDate birthDate;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
