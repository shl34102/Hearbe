package com.ssafy.d108.backend.global.util;

import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import static org.junit.jupiter.api.Assertions.*;

public class AESUtilTest {

    @Test
    public void testEncryptionDecryption() {
        AESUtil aesUtil = new AESUtil();
        // Manually inject secret key (32 bytes for AES-256)
        ReflectionTestUtils.setField(aesUtil, "secretKey", "thisisaverysecurekeyforaes256bit");

        String original = "1234-5678-1234-5678";

        try {
            String encrypted = aesUtil.encrypt(original);
            System.out.println("Encrypted: " + encrypted);

            String decrypted = aesUtil.decrypt(encrypted);
            System.out.println("Decrypted: " + decrypted);

            assertEquals(original, decrypted);
        } catch (Exception e) {
            e.printStackTrace();
            fail("Encryption/Decryption failed: " + e.getMessage());
        }
    }
}
