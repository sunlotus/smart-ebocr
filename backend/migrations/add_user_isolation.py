# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

"""
多账户数据隔离迁移脚本

执行方式:
    python -m backend.migrations.add_user_isolation
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def migrate():
    """添加 user_id 和 family_member_id 字段，实现多账户数据隔离"""
    from backend.app import create_app
    from backend.extensions import db
    from backend.models.user import User
    from backend.models.family_member import FamilyMember

    app = create_app()

    with app.app_context():
        print("开始多账户数据隔离迁移...")

        # 1. 创建 family_members 表
        print("1. 创建 family_members 表...")
        FamilyMember.__table__.create(db.engine, checkfirst=True)

        # 2. 添加外键字段到现有表
        print("2. 添加外键字段...")

        # daily_usage 表
        try:
            db.session.execute(db.text("ALTER TABLE daily_usage ADD COLUMN user_id INTEGER"))
            print("  - daily_usage.user_id 添加成功")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                print(f"  - daily_usage.user_id 已存在")

        try:
            db.session.execute(db.text("ALTER TABLE daily_usage ADD COLUMN family_member_id INTEGER"))
            print("  - daily_usage.family_member_id 添加成功")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                print(f"  - daily_usage.family_member_id 已存在")

        try:
            db.session.execute(db.text("ALTER TABLE daily_usage ADD COLUMN meter_id INTEGER"))
            print("  - daily_usage.meter_id 添加成功")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                print(f"  - daily_usage.meter_id 已存在")

        # meters 表
        try:
            db.session.execute(db.text("ALTER TABLE meters ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1"))
            print("  - meters.user_id 添加成功")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                print(f"  - meters.user_id 已存在")

        try:
            db.session.execute(db.text("ALTER TABLE meters ADD COLUMN family_member_id INTEGER"))
            print("  - meters.family_member_id 添加成功")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                print(f"  - meters.family_member_id 已存在")

        # pricing_policy 表
        try:
            db.session.execute(db.text("ALTER TABLE pricing_policy ADD COLUMN user_id INTEGER"))
            print("  - pricing_policy.user_id 添加成功")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                print(f"  - pricing_policy.user_id 已存在")

        try:
            db.session.execute(db.text("ALTER TABLE pricing_policy ADD COLUMN family_member_id INTEGER"))
            print("  - pricing_policy.family_member_id 添加成功")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                print(f"  - pricing_policy.family_member_id 已存在")

        db.session.commit()

        # 3. 创建系统默认用户
        print("3. 创建系统默认用户...")
        system_user = User.query.filter_by(afdian_uid='system_default').first()
        if not system_user:
            system_user = User(
                afdian_uid='system_default',
                name='系统默认',
                plan_name='premium'
            )
            db.session.add(system_user)
            db.session.flush()
            print(f"  - 系统默认用户创建成功 (user_id={system_user.id})")
        else:
            print(f"  - 系统默认用户已存在 (user_id={system_user.id})")

        # 4. 迁移现有数据
        print("4. 迁移现有数据到系统默认用户...")

        # 迁移 daily_usage
        result = db.session.execute(db.text(
            "UPDATE daily_usage SET user_id = :user_id WHERE user_id IS NULL"
        ), {"user_id": system_user.id})
        print(f"  - 迁移 daily_usage: {result.rowcount} 条")

        # 迁移 meters
        result = db.session.execute(db.text(
            "UPDATE meters SET user_id = :user_id WHERE user_id IS NULL OR user_id = 1"
        ), {"user_id": system_user.id})
        print(f"  - 迁移 meters: {result.rowcount} 条")

        db.session.commit()

        # 5. 创建索引
        print("5. 创建索引...")
        indexes = [
            ("CREATE INDEX IF NOT EXISTS ix_daily_usage_user ON daily_usage(user_id)", "daily_usage.user_id"),
            ("CREATE INDEX IF NOT EXISTS ix_daily_usage_member ON daily_usage(family_member_id)", "daily_usage.family_member_id"),
            ("CREATE INDEX IF NOT EXISTS ix_daily_usage_meter ON daily_usage(meter_id)", "daily_usage.meter_id"),
            ("CREATE INDEX IF NOT EXISTS ix_meters_user ON meters(user_id)", "meters.user_id"),
            ("CREATE INDEX IF NOT EXISTS ix_meters_member ON meters(family_member_id)", "meters.family_member_id"),
            ("CREATE INDEX IF NOT EXISTS ix_policy_user ON pricing_policy(user_id)", "pricing_policy.user_id"),
            ("CREATE INDEX IF NOT EXISTS ix_policy_member ON pricing_policy(family_member_id)", "pricing_policy.family_member_id"),
        ]

        for sql, name in indexes:
            try:
                db.session.execute(db.text(sql))
                print(f"  - {name}")
            except Exception as e:
                if "already exists" not in str(e):
                    print(f"  - {name}: {e}")

        db.session.commit()

        # 6. 修复唯一约束：替换 date 单列唯一为联合唯一
        print("6. 修复唯一约束...")
        try:
            db.session.execute(db.text('DROP INDEX IF EXISTS ix_daily_usage_date'))
            print("  - 删除旧的 date 单列唯一索引")
        except Exception as e:
            print(f"  - 删除旧索引失败: {e}")

        try:
            db.session.execute(db.text(
                'CREATE UNIQUE INDEX IF NOT EXISTS uq_usage_user_date '
                'ON daily_usage(user_id, family_member_id, date)'
            ))
            print("  - 创建联合唯一索引 (user_id, family_member_id, date)")
        except Exception as e:
            print(f"  - 创建联合索引失败: {e}")

        try:
            db.session.execute(db.text(
                'CREATE INDEX IF NOT EXISTS ix_daily_usage_date ON daily_usage(date)'
            ))
            print("  - 重建 date 普通索引（非唯一）")
        except Exception as e:
            print(f"  - 重建索引失败: {e}")

        db.session.commit()

        print("\n多账户数据隔离迁移完成!")
        print(f"系统默认用户 ID: {system_user.id}")
        print("提示: 请重启后端服务使更改生效")


if __name__ == '__main__':
    migrate()
