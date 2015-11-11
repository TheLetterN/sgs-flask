import pytest
from datetime import datetime, timedelta
from flask import current_app
from app.auth.models import (
    EmailRequest,
    get_user_from_confirmation_token,
    Serializer,
    User
)
from tests.conftest import app, db  # noqa


class TestUserWithDB():
    """Test User model methods that need to access the database."""
    def test_email_request_too_many(self, db):
        """Return True if too many requests made by sender, False if not."""
        user = make_dummy_user()
        for i in range(0, 10):
            user.email_requests.append(EmailRequest('confirm account'))
        db.session.add(user)
        db.session.commit()
        assert not user.email_request_too_many('confirm account',
                                               days=30,
                                               maximum=10)
        assert user.email_request_too_many('confirm account',
                                           days=30,
                                           maximum=9)

    def test_email_request_too_many_first_request(self, db):
        """Return False if no previous requests have been made."""
        user = make_dummy_user()
        db.session.add(user)
        db.session.commit()
        assert user.email_requests.filter_by(sender='confirm account')\
            .count() == 0
        assert not user.email_request_too_many('confirm account',
                                               days=30,
                                               maximum=10)

    def test_email_request_too_many_prunes_old_requests(self, db):
        """Prune old requests and return False if remaining < maximum."""
        user = make_dummy_user()
        old_req = datetime.utcnow() - timedelta(days=30)
        user.email_requests.append(EmailRequest('confirm account',
                                                time=old_req))
        for i in range(0, 10):
            user.email_requests.append(EmailRequest('confirm account'))
        db.session.add(user)
        db.session.commit()
        assert not user.email_request_too_many('confirm account',
                                               days=29,
                                               maximum=10)
        user.email_requests.append(EmailRequest('confirm account'))
        assert user.email_request_too_many('confirm account',
                                           days=29,
                                           maximum=10)

    def test_email_request_too_soon(self, db):
        """Return False if not too soon, True if too soon."""
        user = make_dummy_user()
        req_time = datetime.utcnow() - timedelta(minutes=6)
        user.email_requests.append(EmailRequest('confirm account',
                                                time=req_time))
        db.session.add(user)
        db.session.commit()
        assert user.email_request_too_soon('confirm account',
                                           minutes=10)
        assert not user.email_request_too_soon('confirm account',
                                               minutes=5)

    def test_email_request_too_soon_first_request(self, db):
        """Return False if no previous requests have been logged."""
        user = make_dummy_user()
        db.session.add(user)
        db.session.commit()
        assert user.email_requests.filter_by(sender='confirm account')\
            .count() == 0
        assert not user.email_request_too_soon('confirm account',
                                               minutes=10)

    def test_email_request_too_soon_different_senders(self, db):
        """A recent request from one sender shouldn't affect other senders."""
        user = make_dummy_user()
        db.session.add(user)
        db.session.commit()
        user.email_requests.append(EmailRequest('confirm account'))
        assert not user.email_request_too_soon('reset password',
                                               minutes=5)

    def test_get_user_from_confirmation_token_bad_or_wrong_token(self):
        """get_user_from... should raise exception with bad/wrong token."""
        s = Serializer(current_app.config['SECRET_KEY'])
        wrongtoken = s.dumps({'whee': 'beep!'})
        with pytest.raises(KeyError):
            get_user_from_confirmation_token(wrongtoken)
        with pytest.raises(ValueError):
            get_user_from_confirmation_token('badtoken')

    def test_get_user_from_confirmation_token(self, db):
        """get_user_from... raises exeption if user already confirmed."""
        user = make_dummy_user()
        user.id = 42
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        token = user.generate_account_confirmation_token()
        with pytest.raises(ValueError):
            get_user_from_confirmation_token(token)

    def test_get_user_from_confirmation_token_with_valid_token(self, db):
        """get_user_from_confirmation_token should work given a valid token."""
        user1 = make_dummy_user()
        db.session.add(user1)
        db.session.commit()
        token = user1.generate_account_confirmation_token()
        user2 = get_user_from_confirmation_token(token)
        assert user1.id == user2.id

    def test_log_email_request(self, db):
        """log_email_request appends request to user's email_requests."""
        user = make_dummy_user()
        db.session.add(user)
        db.session.commit()
        assert user.email_requests.count() == 0
        user.log_email_request('confirm account')
        assert user.email_requests.count() == 1
        user.log_email_request('confirm account')
        assert user.email_requests.count() == 2

    def test_prune_email_requests(self, db):
        """Email requests older than timespan specified should be deleted."""
        user = make_dummy_user()
        forty_days_ago = datetime.utcnow() - timedelta(days=40)
        for i in range(0, 4):
            user.email_requests.append(EmailRequest('confirm email',
                                                    time=forty_days_ago))
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        for i in range(0, 6):
            user.email_requests.append(EmailRequest('confirm email',
                                                    time=thirty_days_ago))
        db.session.add(user)
        db.session.commit()
        assert user.email_requests.filter_by(sender='confirm email')\
            .count() == 10
        user.prune_email_requests('confirm email', days=31)
        assert user.email_requests.filter_by(sender='confirm email')\
            .count() == 6


def make_dummy_user():
    """Create a basic dummy for testing.

    Returns:
        User: A basic user with no confirmed account or privileges.
    """
    user = User()
    user.name = 'AzureDiamond'
    user.set_password('hunter2')
    user.email = 'gullible@bash.org'
    return user
