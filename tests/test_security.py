from app.security import hash_password, verify_password


def test_password_is_hashed():
    password = "DemoPassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert hashed.startswith("$argon2id$")


def test_correct_password_accepted():
    password = "DemoPassword123!"
    hashed = hash_password(password)
    assert verify_password(password, hashed)


def test_incorrect_password_rejected():
    hashed = hash_password("DemoPassword123!")
    assert not verify_password("WrongPassword123!", hashed)
