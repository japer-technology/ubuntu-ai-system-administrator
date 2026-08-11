from __future__ import annotations

import unittest

from friend import auth


class AuthTests(unittest.TestCase):
    def test_fixed_scrypt_record_and_verification(self) -> None:
        record = auth.hash_password("correct horse battery staple", salt=b"\x01" * 16)
        self.assertEqual(
            record,
            "scrypt$16384$8$1$"
            + "01" * 16
            + "$"
            + "0013c75d16355ab7ccc4a5c1497403a79251d86186522e0c87c4d7c41e125015",
        )
        self.assertTrue(auth.valid_password_record(record))
        self.assertTrue(auth.verify_password("correct horse battery staple", record))
        self.assertFalse(auth.verify_password("wrong", record))

    def test_malformed_or_weakened_records_fail_closed(self) -> None:
        record = auth.hash_password("long enough password")
        for invalid in (
            "",
            record.replace("$16384$", "$8192$"),
            record.replace("$8$", "$4$"),
            "pbkdf2$16384$8$1$00$00",
            "scrypt$bad$8$1$00$00",
        ):
            self.assertFalse(auth.valid_password_record(invalid))
            self.assertFalse(auth.verify_password("long enough password", invalid))

    def test_session_digest_is_keyed(self) -> None:
        token = auth.new_session_token()
        self.assertNotEqual(
            auth.token_digest(token, b"a" * 32),
            auth.token_digest(token, b"b" * 32),
        )
        with self.assertRaises(ValueError):
            auth.token_digest(token, b"short")


if __name__ == "__main__":
    unittest.main()
