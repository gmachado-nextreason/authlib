from authlib.oauth2.rfc6749.grants import ImplicitGrant

from .models import Client, User, db
from .oauth2_server import TestCase, create_authorization_server


class ImplicitTest(TestCase):
    def prepare_data(self, is_confidential=False, response_type="token"):
        server = create_authorization_server(self.app)
        server.register_grant(ImplicitGrant)
        self.server = server

        user = User(username="foo")
        db.add(user)
        db.commit()
        if is_confidential:
            client_secret = "implicit-secret"
            token_endpoint_auth_method = "client_secret_basic"
        else:
            client_secret = ""
            token_endpoint_auth_method = "none"

        client = Client(
            user_id=user.id,
            client_id="implicit-client",
            client_secret=client_secret,
        )
        client.set_client_metadata(
            {
                "redirect_uris": ["http://localhost/authorized"],
                "scope": "profile",
                "response_types": [response_type],
                "grant_types": ["implicit"],
                "token_endpoint_auth_method": token_endpoint_auth_method,
            }
        )
        self.authorize_url = (
            "/oauth/authorize?response_type=token" "&client_id=implicit-client"
        )
        db.add(client)
        db.commit()

    def test_get_authorize(self):
        self.prepare_data()
        rv = self.client.get(self.authorize_url)
        self.assertEqual(rv.json(), "ok")

    def test_confidential_client(self):
        self.prepare_data(True)
        rv = self.client.get(self.authorize_url)
        self.assertIn("invalid_client", rv.json())

    def test_unsupported_client(self):
        self.prepare_data(response_type="code")
        rv = self.client.get(self.authorize_url)
        self.assertIn("unauthorized_client", rv.json())

    def test_invalid_authorize(self):
        self.prepare_data()
        rv = self.client.post(self.authorize_url)
        self.assertIn("#error=access_denied", rv.headers["location"])

        self.server.scopes_supported = ["profile"]
        rv = self.client.post(self.authorize_url + "&scope=invalid")
        self.assertIn("#error=invalid_scope", rv.headers["location"])

    def test_authorize_token(self):
        self.prepare_data()
        rv = self.client.post(self.authorize_url, data={"user_id": "1"})
        self.assertIn("access_token=", rv.headers["location"])

        url = self.authorize_url + "&state=bar&scope=profile"
        rv = self.client.post(url, data={"user_id": "1"})
        self.assertIn("access_token=", rv.headers["location"])
        self.assertIn("state=bar", rv.headers["location"])
        self.assertIn("scope=profile", rv.headers["location"])

    def test_token_generator(self):
        m = "tests.fastapi.test_oauth2.oauth2_server:token_generator"
        self.app.config.update({"OAUTH2_ACCESS_TOKEN_GENERATOR": m})
        self.prepare_data()
        rv = self.client.post(self.authorize_url, data={"user_id": "1"})
        self.assertIn("access_token=i-implicit.1.", rv.headers["location"])
