package com.ssafy.d108.backend.category.repository;

import com.ssafy.d108.backend.entity.Category;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface CategoryRepository extends JpaRepository<Category, Integer> {

    /**
     * 전체 카테고리 경로로 조회
     * 
     * @param fullPath 전체 카테고리 경로 (예: "식품/생수/음료/생수/국산생수")
     * @return Category 엔티티
     */
    Optional<Category> findByFullPath(String fullPath);

    /**
     * 카테고리 이름으로 검색
     * 
     * @param name 카테고리 이름 (부분 일치)
     * @return 해당 이름을 포함하는 카테고리 리스트
     */
    List<Category> findByNameContaining(String name);
}
