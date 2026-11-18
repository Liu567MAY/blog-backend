"""初始化唯一管理员。

用法：python -m scripts.init_admin
账号密码优先读取 .env 中的 ADMIN_USERNAME / ADMIN_PASSWORD，未配置时交互式输入。
"""

import getpass

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.infrastructure.database.session import SessionLocal
from app.modules.auth import service


def main() -> None:
    settings = get_settings()
    username = settings.admin_username or input("管理员用户名: ").strip()
    password = settings.admin_password or getpass.getpass("管理员密码: ")
    if not settings.admin_password:
        confirm = getpass.getpass("再次输入密码: ")
        if password != confirm:
            print("两次输入的密码不一致")
            raise SystemExit(1)
    if not username or not password:
        print("用户名和密码不能为空")
        raise SystemExit(1)

    db = SessionLocal()
    try:
        service.create_admin(db, username, password)
        print(f"管理员 {username} 创建成功")
    except AppError as exc:
        print(f"初始化失败: {exc.detail}")
        raise SystemExit(1) from exc
    finally:
        db.close()


if __name__ == "__main__":
    main()
