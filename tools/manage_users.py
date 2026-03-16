#!/usr/bin/env python
"""
密码管理工具

使用方法:
    # 生成密码哈希
    python tools/manage_users.py hash "MyPassword123!"

    # 验证密码
    python tools/manage_users.py verify <hash> "MyPassword123!"

    # 列出用户
    python tools/manage_users.py list
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import hash_password, verify_password, is_password_strong


def print_usage():
    print("""
密码管理工具

使用方法:
    # 生成密码哈希
    python tools/manage_users.py hash "MyPassword123!"

    # 验证密码
    python tools/manage_users.py verify <hash> "MyPassword123!"

    # 检查密码强度
    python tools/manage_users.py check "MyPassword123!"

    # 列出.env 中的用户
    python tools/manage_users.py list
    """)


def cmd_hash(password: str):
    """生成密码哈希"""
    # 检查密码强度
    is_strong, msg = is_password_strong(password)
    if not is_strong:
        print(f"⚠️  密码强度警告：{msg}")
        print("建议使用更强的密码（大小写字母 + 数字/特殊字符）\n")

    pwd_hash = hash_password(password)
    print(f"密码哈希:\n{pwd_hash}")
    print(f"\n在 .env 中使用格式：ADMIN_USERS=admin:{pwd_hash}")


def cmd_verify(pwd_hash: str, password: str):
    """验证密码"""
    if verify_password(password, pwd_hash):
        print("✅ 密码验证通过")
    else:
        print("❌ 密码验证失败")


def cmd_check(password: str):
    """检查密码强度"""
    is_strong, msg = is_password_strong(password)
    if is_strong:
        print(f"✅ {msg}")
    else:
        print(f"❌ {msg}")


def cmd_list():
    """列出.env 中的用户"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')

    if not os.path.exists(env_path):
        print("❌ .env 文件不存在")
        return

    print(f"读取配置：{env_path}\n")

    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('ADMIN_USERS='):
                users_str = line.split('=', 1)[1]
                print(f"管理员账户：{users_str}")

                # 解析用户
                for pair in users_str.split(','):
                    if ':' in pair:
                        u, p = pair.split(':', 1)
                        if p.startswith('pbkdf2:'):
                            print(f"  - {u}: [已哈希] ✅")
                        else:
                            print(f"  - {u}: [明文] ⚠️  建议升级为哈希密码")
                return

    print("⚠️  未找到 ADMIN_USERS 配置")


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == 'hash':
        if len(sys.argv) < 3:
            print("❌ 请提供密码参数")
            print_usage()
            sys.exit(1)
        cmd_hash(sys.argv[2])

    elif cmd == 'verify':
        if len(sys.argv) < 4:
            print("❌ 请提供哈希和密码参数")
            print_usage()
            sys.exit(1)
        cmd_verify(sys.argv[2], sys.argv[3])

    elif cmd == 'check':
        if len(sys.argv) < 3:
            print("❌ 请提供密码参数")
            print_usage()
            sys.exit(1)
        cmd_check(sys.argv[2])

    elif cmd == 'list':
        cmd_list()

    else:
        print(f"❌ 未知命令：{cmd}")
        print_usage()
        sys.exit(1)


if __name__ == '__main__':
    main()
