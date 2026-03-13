import pytest
from django.conf import settings
from rest_framework import status


@pytest.mark.django_db
class TestAuthCookiesAPI:
    def test_login_setea_cookies_http_only_y_devuelve_usuario(self, api_client, usuario):
        response = api_client.post(
            "/api/token/",
            {"email": usuario.email, "password": "pass1234"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "user" in response.data
        assert response.data["user"]["email"] == usuario.email
        assert "access" not in response.data
        assert "refresh" not in response.data

        access_cookie = response.cookies.get(settings.AUTH_COOKIE_ACCESS_NAME)
        refresh_cookie = response.cookies.get(settings.AUTH_COOKIE_REFRESH_NAME)

        assert access_cookie is not None
        assert refresh_cookie is not None
        assert access_cookie["httponly"]
        assert refresh_cookie["httponly"]

    def test_me_usa_access_cookie_para_autenticar(self, api_client, usuario):
        api_client.post(
            "/api/token/",
            {"email": usuario.email, "password": "pass1234"},
            format="json",
        )

        response = api_client.get("/api/auth/me/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["user"]["email"] == usuario.email

    def test_refresh_usa_cookie_y_renueva_access_cookie(self, api_client, usuario):
        login_response = api_client.post(
            "/api/token/",
            {"email": usuario.email, "password": "pass1234"},
            format="json",
        )

        csrf_token = login_response.cookies.get("csrftoken")
        assert csrf_token is not None

        response = api_client.post(
            "/api/token/refresh/",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token.value,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "Sesion renovada."
        assert response.cookies.get(settings.AUTH_COOKIE_ACCESS_NAME) is not None

    def test_logout_limpia_cookies(self, api_client, usuario):
        api_client.post(
            "/api/token/",
            {"email": usuario.email, "password": "pass1234"},
            format="json",
        )

        response = api_client.post("/api/auth/logout/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        access_cookie = response.cookies.get(settings.AUTH_COOKIE_ACCESS_NAME)
        refresh_cookie = response.cookies.get(settings.AUTH_COOKIE_REFRESH_NAME)
        assert access_cookie is not None
        assert refresh_cookie is not None
        assert access_cookie.value == ""
        assert refresh_cookie.value == ""

    def test_me_sin_cookie_devuelve_401(self, api_client):
        response = api_client.get("/api/auth/me/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
