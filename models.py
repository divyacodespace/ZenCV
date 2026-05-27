"""Database models for users and saved analysis history."""

from __future__ import annotations

from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime)

    analyses = db.relationship("AnalysisRecord", backref="user",
                                lazy="dynamic", cascade="all, delete-orphan",
                                order_by="AnalysisRecord.created_at.desc()")
    jd_matches = db.relationship("JDMatchRecord", backref="user",
                                  lazy="dynamic", cascade="all, delete-orphan",
                                  order_by="JDMatchRecord.created_at.desc()")

    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class AnalysisRecord(db.Model):
    __tablename__ = "analyses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                         nullable=True, index=True)
    filename = db.Column(db.String(255), nullable=False)
    ats_score = db.Column(db.Integer, nullable=False)
    word_count = db.Column(db.Integer, nullable=False)
    payload_json = db.Column(db.Text, nullable=False)   # full AnalysisResult as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class JDMatchRecord(db.Model):
    __tablename__ = "jd_matches"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                         nullable=True, index=True)
    match_score = db.Column(db.Integer, nullable=False)
    jd_preview = db.Column(db.String(280), nullable=False)
    payload_json = db.Column(db.Text, nullable=False)   # full JDMatchResult as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
