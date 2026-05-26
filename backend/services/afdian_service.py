# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

import hashlib
import time
import requests
from flask import current_app


AFDIAN_OAUTH_AUTHORIZE = 'https://ifdian.net/oauth2/authorize'
AFDIAN_OAUTH_TOKEN_URL = 'https://ifdian.net/api/oauth2/access_token'
AFDIAN_API_BASE = 'https://ifdian.net/api/open'


class AfdianService:
    """爱发电 API 服务封装"""

    @staticmethod
    def get_authorize_url(state: str) -> str:
        """生成 OAuth 授权 URL"""
        client_id = current_app.config.get('AFDIAN_OAUTH_CLIENT_ID', '')
        redirect_uri = current_app.config.get('AFDIAN_OAUTH_REDIRECT_URI', '')
        return (
            f'{AFDIAN_OAUTH_AUTHORIZE}'
            f'?client_id={client_id}'
            f'&redirect_uri={redirect_uri}'
            f'&response_type=code'
            f'&state={state}'
        )

    @staticmethod
    def get_token(code: str) -> dict | None:
        """OAuth 用 code 换 access_token"""
        resp = requests.post(AFDIAN_OAUTH_TOKEN_URL, json={
            'client_id': current_app.config.get('AFDIAN_OAUTH_CLIENT_ID', ''),
            'client_secret': current_app.config.get('AFDIAN_OAUTH_CLIENT_SECRET', ''),
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': current_app.config.get('AFDIAN_OAUTH_REDIRECT_URI', ''),
        }, timeout=10)
        data = resp.json()
        if data.get('ec') == 200:
            return data.get('data', {})
        return None

    @staticmethod
    def get_user_info(access_token: str) -> dict | None:
        """获取用户信息"""
        resp = requests.get(f'{AFDIAN_API_BASE}/me', headers={
            'Authorization': f'Bearer {access_token}',
        }, timeout=10)
        data = resp.json()
        if data.get('ec') == 200:
            return data.get('data', {}).get('user', {})
        return None

    @staticmethod
    def compute_sign(token: str, params: str, ts: int, user_id: str) -> str:
        """计算 API 签名：md5(token + params + ts + user_id)"""
        raw = f'{token}{params}{ts}{user_id}'
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    @staticmethod
    def _call_api(endpoint: str, params: dict | None = None) -> dict | None:
        """调用爱发电 Open API"""
        user_id = current_app.config.get('AFDIAN_USER_ID', '')
        token = current_app.config.get('AFDIAN_API_TOKEN', '')
        if not user_id or not token:
            return None

        ts = int(time.time())
        params_str = str(params or {})
        sign = AfdianService.compute_sign(token, params_str, ts, user_id)

        resp = requests.post(
            f'{AFDIAN_API_BASE}/{endpoint}',
            json={
                'user_id': user_id,
                'params': params_str,
                'ts': ts,
                'sign': sign,
            },
            timeout=10,
        )
        data = resp.json()
        if data.get('ec') == 200:
            return data.get('data', {})
        return None

    @staticmethod
    def query_sponsor(page: int = 1) -> dict | None:
        """查询赞助者列表"""
        return AfdianService._call_api('query-sponsor', {'page': page})

    @staticmethod
    def query_order(page: int = 1) -> dict | None:
        """查询订单列表"""
        return AfdianService._call_api('query-order', {'page': page})

    @staticmethod
    def ping() -> dict | None:
        """测试 API 连通性"""
        return AfdianService._call_api('ping')

    @staticmethod
    def determine_plan(sponsor_data: dict, afdian_uid: str) -> tuple[str, str | None]:
        """
        根据赞助数据判定用户档位。
        返回 (plan_name, plan_id)
        """
        if not sponsor_data:
            return 'free', None

        sponsor_list = sponsor_data.get('sponsor_plans', sponsor_data.get('list', []))
        if not sponsor_list:
            return 'free', None

        # 按金额判断档位
        best_plan = 'free'
        best_plan_id = None

        for sponsor in sponsor_list:
            user = sponsor.get('user', {})
            if user.get('user_id') != afdian_uid:
                continue

            current = sponsor.get('current_plan', {})
            plan_id = current.get('plan_id', '')
            amount = float(current.get('amount', 0))

            # 根据月金额判断档位
            if amount >= 9900:  # ¥99+
                best_plan = 'super'
            elif amount >= 3000:  # ¥30+
                best_plan = 'premium'
            elif amount >= 900:  # ¥9+
                best_plan = 'supporter'

            if best_plan != 'free':
                best_plan_id = plan_id
                break

        return best_plan, best_plan_id