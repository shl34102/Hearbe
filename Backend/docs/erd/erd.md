CREATE TABLE `플랫폼` (
	`id`	int	NOT NULL	DEFAULT AUTO_INCREMENT,
	`플랫폼 이름`	varchar(10)	NULL,
	`base_url`	varchar(500)	NOT NULL
);

CREATE TABLE `위시리스트상품` (
	`id`	int	NOT NULL	DEFAULT AUTO_INCREMENT,
	`user_id`	varchar(30)	NOT NULL,
	`platform_id`	int	NOT NULL	DEFAULT AUTO_INCREMENT,
	`상품이름`	varchar(100)	NULL,
	`가격`	int	NULL,
	`상품url`	varchar(500)	NULL	DEFAULT NULL,
	`상품 이미지 url`	varchar(1000)	NULL,
	`생성일시`	timestamp	NOT NULL	DEFAULT TRUE
);

CREATE TABLE `복지카드` (
	`id`	int	NOT NULL	DEFAULT AUTO_INCREMENT,
	`아이디`	varchar(30)	NOT NULL,
	`카드번호`	varchar(50)	NULL,
	`cvc`	varchar(5)	NULL	COMMENT 'CVC 번호 (AES-256 암호화 필수)',
	`카드사`	varchar(30)	NULL,
	`발급일`	date	NOT NULL	COMMENT '발급일자',
	`유효기간`	date	NOT NULL	COMMENT '유효기간',
	`셍성일시`	timestamp	NOT NULL	COMMENT 'CURRENT_TIMESTAMP',
	`수정일시`	timestamp	NOT NULL	DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE `장바구니_상품` (
	`id`	int	NOT NULL	DEFAULT AUTO_INCREMENT,
	`user_id`	varchar(30)	NOT NULL,
	`플랫폼아이디`	int	NOT NULL	DEFAULT AUTO_INCREMENT,
	`상품이름`	varchar(100)	NULL,
	`가격`	int	NULL,
	`수량`	int	NOT NULL	DEFAULT 1,
	`상품url`	varchar(500)	NULL	DEFAULT NULL,
	`상품 이미지 url`	varchar(1000)	NULL,
	`created_at`	timestamp	NOT NULL	DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE `users` (
	`id`	int	NOT NULL	DEFAULT AUTO_INCREMENT,
	`아이디`	varchar(30)	NULL,
	`이메일`	varchar(50)	NULL,
	`비밀번호`	varchar(30)	NULL,
	`전화번호`	varchar(20)	NOT NULL,
	`간편비밀번호`	varchar(6)	NULL	DEFAULT NULL,
	`이름`	varchar(15)	NULL,
	`유저타입`	enum	NOT NULL	DEFAULT 'BLIND',
	`생성일`	timestamp	NOT NULL	DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE `공유세션` (
	`id`	int	NOT NULL	DEFAULT AUTO_INCREMENT,
	`호스트유저`	varchar(30)	NOT NULL,
	`시작시각`	timestamp	NOT NULL	DEFAULT CURRENT_TIMESTAMP,
	`종료시각`	timestamp	NULL	DEFAULT NULL,
	`세션상태`	enum	NOT NULL	DEFAULT 'active'
);

CREATE TABLE `주문상품` (
	`id`	int	NOT NULL	DEFAULT AUTO_INCREMENT,
	`order_id`	int	NOT NULL,
	`상품이름`	varchar(100)	NULL,
	`상품url`	varchar(500)	NOT NULL	DEFAULT NULL,
	`배송조회url`	varchar(1000)	NULL,
	`가격`	int	NOT NULL,
	`상품 이미지 url`	varchar(1000)	NULL,
	`수량`	int	NOT NULL	DEFAULT 1
);

CREATE TABLE `프로필` (
	`id`	int	NOT NULL	DEFAULT AUTO_INCREMENT,
	`아이디`	varchar(30)	NOT NULL,
	`성별`	enum	NULL,
	`몸무게`	float	NULL	DEFAULT NULL,
	`생년월일`	date	NULL	DEFAULT NULL,
	`updated_at`	timestamp	NULL	DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE `주문` (
	`id`	int	NOT NULL	DEFAULT AUTO_INCREMENT,
	`platform_id`	int	NOT NULL	DEFAULT AUTO_INCREMENT,
	`user_id`	varchar(30)	NOT NULL,
	`주문내역url`	varchar(1000)	NULL	DEFAULT NULL,
	`created_at`	timestamp	NOT NULL	DEFAULT CURRENT_TIMESTAMP,
	`updated_at`	timestamp	NOT NULL	DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE `플랫폼` ADD CONSTRAINT `PK_플랫폼` PRIMARY KEY (
	`id`
);

ALTER TABLE `위시리스트상품` ADD CONSTRAINT `PK_위시리스트상품` PRIMARY KEY (
	`id`
);

ALTER TABLE `복지카드` ADD CONSTRAINT `PK_복지카드` PRIMARY KEY (
	`id`
);

ALTER TABLE `장바구니_상품` ADD CONSTRAINT `PK_장바구니_상품` PRIMARY KEY (
	`id`
);

ALTER TABLE `users` ADD CONSTRAINT `PK_USERS` PRIMARY KEY (
	`id`
);

ALTER TABLE `공유세션` ADD CONSTRAINT `PK_공유세션` PRIMARY KEY (
	`id`
);

ALTER TABLE `주문상품` ADD CONSTRAINT `PK_주문상품` PRIMARY KEY (
	`id`
);

ALTER TABLE `프로필` ADD CONSTRAINT `PK_프로필` PRIMARY KEY (
	`id`
);

ALTER TABLE `주문` ADD CONSTRAINT `PK_주문` PRIMARY KEY (
	`id`,
	`platform_id`
);

ALTER TABLE `주문` ADD CONSTRAINT `FK_플랫폼_TO_주문_1` FOREIGN KEY (
	`platform_id`
)
REFERENCES `플랫폼` (
	`id`
);

