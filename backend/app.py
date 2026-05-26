# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

import os
import time
from flask import Flask, request, g, jsonify
from flask_cors import CORS
from backend.extensions import db
from backend.config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, UPLOAD_FOLDER, DATA_DIR, SECRET_KEY, APP_VERSION
from backend.utils.logger import get_logger, get_request_logger, log_exception


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    app.secret_key = SECRET_KEY

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    CORS(app)
    db.init_app(app)

    @app.route('/api/version')
    def version():
        return jsonify({'version': APP_VERSION})

    from backend.api import screenshot, usage, billing, policy
    from backend.api.meters import bp as meters_bp
    from backend.api import family_members
    app.register_blueprint(screenshot.bp, url_prefix='/api/screenshot')
    app.register_blueprint(usage.bp, url_prefix='/api/usage')
    app.register_blueprint(billing.bp, url_prefix='/api/billing')
    app.register_blueprint(policy.bp, url_prefix='/api/policy')
    app.register_blueprint(meters_bp, url_prefix='/api/meters')
    app.register_blueprint(family_members.bp, url_prefix='/api/family-members')

    # Setup logging
    logger = get_logger(__name__)
    request_logger = get_request_logger()

    @app.before_request
    def log_request_start():
        """Record request start time for duration tracking."""
        g.start_time = time.time()

        # Log request details
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        request_logger.info(
            f"Request: {request.method} {request.path} | "
            f"IP: {client_ip} | "
            f"Args: {dict(request.args)}"
        )

    @app.after_request
    def log_request_end(response):
        """Log request completion with duration."""
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            request_logger.info(
                f"Response: {request.method} {request.path} | "
                f"Status: {response.status_code} | "
                f"Duration: {duration:.3f}s"
            )
        return response

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Global exception handler."""
        log_exception(logger, e, {
            'path': request.path,
            'method': request.method,
            'args': dict(request.args),
        })
        return jsonify({'error': str(e)}), 500

    with app.app_context():
        from backend.models.daily_usage import DailyUsage  # noqa: F401
        from backend.models.pricing_policy import PricingPolicy  # noqa: F401
        from backend.models.user import User  # noqa: F401
        from backend.models.meter import Meter  # noqa: F401
        from backend.models.family_member import FamilyMember  # noqa: F401
        db.create_all()
        _migrate_heating_valley_rate()
        _seed_default_policy()

    return app


def _seed_default_policy():
    from backend.models.pricing_policy import PricingPolicy
    from backend.config import DEFAULT_POLICY
    if not PricingPolicy.query.filter_by(is_active=True).first():
        p = PricingPolicy(
            name=DEFAULT_POLICY['name'],
            region=DEFAULT_POLICY['region'],
            tier1_rate=DEFAULT_POLICY['tier1_rate'],
            tier1_limit=DEFAULT_POLICY['tier1_limit'],
            tier2_rate=DEFAULT_POLICY['tier2_rate'],
            tier2_limit=DEFAULT_POLICY['tier2_limit'],
            tier3_rate=DEFAULT_POLICY['tier3_rate'],
            peak_rate=DEFAULT_POLICY['peak_rate'],
            valley_rate=DEFAULT_POLICY['valley_rate'],
            heating_valley_rate=DEFAULT_POLICY['heating_valley_rate'],
            sharp_rate=DEFAULT_POLICY['sharp_rate'],
            flat_rate=DEFAULT_POLICY.get('flat_rate', 0.5469),
            peak_hours=str(DEFAULT_POLICY['peak_hours']),
            valley_hours=str(DEFAULT_POLICY['valley_hours']),
            is_active=True,
        )
        db.session.add(p)
        db.session.commit()


def _migrate_heating_valley_rate():
    """Add heating_valley_rate column to existing pricing_policy table."""
    import sqlite3
    from backend.config import DB_PATH
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(pricing_policy)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'heating_valley_rate' not in columns:
            cursor.execute("ALTER TABLE pricing_policy ADD COLUMN heating_valley_rate FLOAT DEFAULT 0.3469")
            conn.commit()
            print("Migration: added heating_valley_rate column")
        conn.close()
    except Exception:
        pass  # Table may not exist yet, create_all will handle it


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)