from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.payments.services.provider_service import verify_paypal_signature

VALID_HEADERS = {
    "Paypal-Transmission-Id": "abc123",
    "Paypal-Transmission-Time": "2026-01-01T00:00:00Z",
    "Paypal-Cert-Url": "https://api.paypal.com/v1/notifications/certs/CERT-1",
    "Paypal-Auth-Algo": "SHA256withRSA",
    "Paypal-Transmission-Sig": "fake-signature",
}


@override_settings(PAYPAL_WEBHOOK_ID="WH-TEST-ID")
class VerifyPaypalSignatureTests(TestCase):
    def test_rejects_when_webhook_id_not_configured(self):
        with override_settings(PAYPAL_WEBHOOK_ID=""):
            self.assertFalse(verify_paypal_signature(VALID_HEADERS, "{}"))

    def test_rejects_missing_headers(self):
        self.assertFalse(verify_paypal_signature({}, "{}"))

    def test_rejects_non_paypal_cert_url(self):
        # This is the exact forgery the bug allowed: any non-empty signature
        # header used to be accepted outright.
        headers = {**VALID_HEADERS, "Paypal-Cert-Url": "https://evil.example.com/fake-cert"}
        self.assertFalse(verify_paypal_signature(headers, "{}"))

    def test_rejects_non_https_cert_url(self):
        headers = {**VALID_HEADERS, "Paypal-Cert-Url": "http://api.paypal.com/v1/notifications/certs/CERT-1"}
        self.assertFalse(verify_paypal_signature(headers, "{}"))

    def test_rejects_lookalike_paypal_domain(self):
        headers = {**VALID_HEADERS, "Paypal-Cert-Url": "https://api.paypal.com.evil.example.com/cert"}
        self.assertFalse(verify_paypal_signature(headers, "{}"))

    @patch("apps.payments.services.provider_service.paypalrestsdk.WebhookEvent.verify", return_value=True)
    def test_accepts_when_sdk_verifies_and_cert_url_is_paypal(self, mock_verify):
        self.assertTrue(verify_paypal_signature(VALID_HEADERS, "{}"))
        mock_verify.assert_called_once_with(
            "abc123",
            "2026-01-01T00:00:00Z",
            "WH-TEST-ID",
            "{}",
            "https://api.paypal.com/v1/notifications/certs/CERT-1",
            "fake-signature",
            "SHA256withRSA",
        )

    @patch("apps.payments.services.provider_service.paypalrestsdk.WebhookEvent.verify", return_value=False)
    def test_rejects_when_sdk_verification_fails(self, mock_verify):
        self.assertFalse(verify_paypal_signature(VALID_HEADERS, "{}"))

    @patch(
        "apps.payments.services.provider_service.paypalrestsdk.WebhookEvent.verify",
        side_effect=Exception("cert fetch timed out"),
    )
    def test_rejects_when_sdk_raises(self, mock_verify):
        self.assertFalse(verify_paypal_signature(VALID_HEADERS, "{}"))
