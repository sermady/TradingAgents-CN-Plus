# -*- coding: utf-8 -*-
"""
安全改进脚本
1. 生成新的JWT_SECRET和CSRF_SECRET
2. 确保JWT_SECRET和CSRF_SECRET使用不同的值
"""

import secrets
import re


def generate_secure_secret():
    """生成安全的随机密钥"""
    return secrets.token_urlsafe(32)


def update_env_file():
    """更新.env文件"""
    env_path = ".env"

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 生成新的密钥
        new_jwt_secret = generate_secure_secret()
        new_csrf_secret = generate_secure_secret()

        # 确保两个密钥不同
        while new_jwt_secret == new_csrf_secret:
            new_csrf_secret = generate_secure_secret()

        print(f"[OK] Generated new JWT_SECRET: {new_jwt_secret[:20]}...")
        print(f"[OK] Generated new CSRF_SECRET: {new_csrf_secret[:20]}...")

        # 替换JWT_SECRET
        content = re.sub(r"JWT_SECRET=.*", f"JWT_SECRET={new_jwt_secret}", content)

        # 替换CSRF_SECRET
        content = re.sub(r"CSRF_SECRET=.*", f"CSRF_SECRET={new_csrf_secret}", content)

        # 写回文件
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"\n[OK] Successfully updated .env file")
        print(f"[WARN] JWT_SECRET and CSRF_SECRET now use different values")
        print(f"[WARN] Please restart the application to apply changes")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to update .env file: {e}")
        return False


if __name__ == "__main__":
    print("Starting security key update...")
    if update_env_file():
        print("\n[SUCCESS] Security keys updated!")
    else:
        print("\n[FAILED] Security key update failed!")
