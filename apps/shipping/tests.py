from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.shipping.services import ups_client, ups_service
from apps.shipping.services.ups_client import UPSError, UPSNotConfigured

UPS_TEST_SETTINGS = dict(
    UPS_MODE="sandbox",
    UPS_BASE_URL="https://wwwcie.ups.com",
    UPS_CLIENT_ID="test-client-id",
    UPS_CLIENT_SECRET="test-client-secret",
    UPS_ACCOUNT_NUMBER="",
    UPS_TRANSACTION_SRC="kofora-test",
    UPS_SHIPPER_NAME="Kofora",
    UPS_SHIPPER_ADDRESS_LINE="1 Test Street",
    UPS_SHIPPER_CITY="Atlanta",
    UPS_SHIPPER_STATE="GA",
    UPS_SHIPPER_POSTAL_CODE="30301",
    UPS_SHIPPER_COUNTRY="US",
    UPS_WEIGHT_UNIT="LBS",
    UPS_DIMENSION_UNIT="IN",
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)

DESTINATION = {
    "full_name": "Jane Doe",
    "address_line_1": "500 Main Street",
    "city": "Chicago",
    "state_province": "IL",
    "postal_code": "60601",
    "country": "US",
}


def fake_response(status_code=200, json_body=None, text=""):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    if json_body is None:
        response.json.side_effect = ValueError("no json")
    else:
        response.json.return_value = json_body
    return response


@override_settings(**UPS_TEST_SETTINGS)
class UPSClientTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("apps.shipping.services.ups_client.requests.post")
    def test_token_is_cached_between_calls(self, mock_post):
        mock_post.return_value = fake_response(200, {"access_token": "tok-1", "expires_in": 14399})

        self.assertEqual(ups_client.get_access_token(), "tok-1")
        self.assertEqual(ups_client.get_access_token(), "tok-1")
        self.assertEqual(mock_post.call_count, 1)

    @patch("apps.shipping.services.ups_client.requests.post")
    def test_rejected_credentials_surface_ups_error_code(self, mock_post):
        mock_post.return_value = fake_response(
            401,
            {"response": {"errors": [{"code": "10401", "message": "ClientId is Invalid"}]}},
        )

        with self.assertRaises(UPSError) as ctx:
            ups_client.get_access_token()
        self.assertIn("10401: ClientId is Invalid", str(ctx.exception))

    @override_settings(UPS_CLIENT_SECRET="OrfAJİJAZC5")
    def test_non_ascii_secret_is_rejected_before_any_request(self):
        with patch("apps.shipping.services.ups_client.requests.post") as mock_post:
            with self.assertRaises(UPSNotConfigured):
                ups_client.get_access_token()
            mock_post.assert_not_called()

    @override_settings(UPS_CLIENT_ID="", UPS_CLIENT_SECRET="")
    def test_missing_credentials_are_rejected(self):
        with self.assertRaises(UPSNotConfigured):
            ups_client.get_access_token()

    @patch("apps.shipping.services.ups_client.requests.request")
    @patch("apps.shipping.services.ups_client.requests.post")
    def test_revoked_token_is_refreshed_once(self, mock_post, mock_request):
        mock_post.side_effect = [
            fake_response(200, {"access_token": "stale", "expires_in": 14399}),
            fake_response(200, {"access_token": "fresh", "expires_in": 14399}),
        ]
        mock_request.side_effect = [
            fake_response(401, {}),
            fake_response(200, {"ok": True}),
        ]

        self.assertEqual(ups_client.ups_request("GET", "/api/track/v1/details/1Z"), {"ok": True})
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(
            mock_request.call_args.kwargs["headers"]["Authorization"], "Bearer fresh"
        )

    @patch("apps.shipping.services.ups_client.requests.request")
    @patch("apps.shipping.services.ups_client.requests.post")
    def test_persistent_401_raises_rather_than_looping(self, mock_post, mock_request):
        mock_post.return_value = fake_response(200, {"access_token": "tok", "expires_in": 14399})
        mock_request.return_value = fake_response(401, {})

        with self.assertRaises(UPSError):
            ups_client.ups_request("GET", "/api/track/v1/details/1Z")
        self.assertEqual(mock_request.call_count, 2)

    def test_sandbox_detection(self):
        self.assertTrue(ups_client.is_sandbox())
        with override_settings(UPS_BASE_URL="https://onlinetools.ups.com"):
            self.assertFalse(ups_client.is_sandbox())


@override_settings(**UPS_TEST_SETTINGS)
class UPSRatingTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("apps.shipping.services.ups_service.ups_request")
    def test_rates_are_normalized_and_sorted_by_cost(self, mock_request):
        mock_request.return_value = {
            "RateResponse": {
                "RatedShipment": [
                    {
                        "Service": {"Code": "02"},
                        "TotalCharges": {"MonetaryValue": "24.50", "CurrencyCode": "USD"},
                    },
                    {
                        "Service": {"Code": "03"},
                        "TotalCharges": {"MonetaryValue": "12.30", "CurrencyCode": "USD"},
                        "GuaranteedDelivery": {"BusinessDaysInTransit": "3"},
                    },
                ]
            }
        }

        rates = ups_service.get_rates(DESTINATION, [{"weight": "5"}])

        self.assertEqual([r["service_code"] for r in rates], ["03", "02"])
        self.assertEqual(rates[0]["service_name"], "UPS Ground")
        self.assertEqual(rates[0]["total_charge"], Decimal("12.30"))
        self.assertEqual(rates[0]["business_days_in_transit"], "3")
        self.assertEqual(rates[1]["service_name"], "UPS 2nd Day Air")

    @patch("apps.shipping.services.ups_service.ups_request")
    def test_single_rated_shipment_object_is_handled(self, mock_request):
        # UPS returns a bare object rather than a list when only one rate matches.
        mock_request.return_value = {
            "RateResponse": {
                "RatedShipment": {
                    "Service": {"Code": "03"},
                    "TotalCharges": {"MonetaryValue": "12.30", "CurrencyCode": "USD"},
                }
            }
        }

        rates = ups_service.get_rates(DESTINATION, [{"weight": "5"}])

        self.assertEqual(len(rates), 1)
        self.assertEqual(rates[0]["service_code"], "03")

    @patch("apps.shipping.services.ups_service.ups_request")
    def test_negotiated_charge_wins_over_published(self, mock_request):
        mock_request.return_value = {
            "RateResponse": {
                "RatedShipment": {
                    "Service": {"Code": "03"},
                    "TotalCharges": {"MonetaryValue": "12.30", "CurrencyCode": "USD"},
                    "NegotiatedRateCharges": {
                        "TotalCharge": {"MonetaryValue": "9.99", "CurrencyCode": "USD"}
                    },
                }
            }
        }

        rate = ups_service.get_rates(DESTINATION, [{"weight": "5"}])[0]

        self.assertEqual(rate["published_charge"], Decimal("12.30"))
        self.assertEqual(rate["negotiated_charge"], Decimal("9.99"))
        self.assertEqual(rate["total_charge"], Decimal("9.99"))

    @override_settings(UPS_ACCOUNT_NUMBER="A1B2C3")
    @patch("apps.shipping.services.ups_service.ups_request")
    def test_account_number_requests_negotiated_rates(self, mock_request):
        mock_request.return_value = {"RateResponse": {"RatedShipment": []}}

        ups_service.get_rates(DESTINATION, [{"weight": "5"}])

        shipment = mock_request.call_args.kwargs["json_body"]["RateRequest"]["Shipment"]
        self.assertEqual(shipment["Shipper"]["ShipperNumber"], "A1B2C3")
        self.assertEqual(
            shipment["ShipmentRatingOptions"]["NegotiatedRatesIndicator"], "Y"
        )

    @patch("apps.shipping.services.ups_service.ups_request")
    def test_dimensions_are_sent_only_when_complete(self, mock_request):
        mock_request.return_value = {"RateResponse": {"RatedShipment": []}}

        ups_service.get_rates(
            DESTINATION,
            [
                {"weight": "5", "length": "10", "width": "8", "height": "6"},
                {"weight": "2", "length": "10"},
            ],
        )

        packages = mock_request.call_args.kwargs["json_body"]["RateRequest"]["Shipment"]["Package"]
        self.assertIn("Dimensions", packages[0])
        self.assertNotIn("Dimensions", packages[1])

    def test_rates_require_at_least_one_package(self):
        with self.assertRaises(UPSError):
            ups_service.get_rates(DESTINATION, [])

    def test_rate_option_requires_service_code(self):
        with self.assertRaises(UPSError):
            ups_service.get_rates(DESTINATION, [{"weight": "5"}], request_option="Rate")


@override_settings(**UPS_TEST_SETTINGS, UPS_RATE_CACHE_SECONDS=3600)
class UPSSingleServiceRateTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("apps.shipping.services.ups_service.ups_request")
    def test_returns_charge_for_requested_service(self, mock_request):
        mock_request.return_value = {
            "RateResponse": {
                "RatedShipment": {
                    "Service": {"Code": "03"},
                    "TotalCharges": {"MonetaryValue": "12.30", "CurrencyCode": "USD"},
                }
            }
        }

        charge = ups_service.get_rate_for_service(DESTINATION, [{"weight": "2"}], "03")

        self.assertEqual(charge, Decimal("12.30"))

    @patch("apps.shipping.services.ups_service.ups_request")
    def test_result_is_cached_by_destination_and_weight(self, mock_request):
        mock_request.return_value = {
            "RateResponse": {
                "RatedShipment": {
                    "Service": {"Code": "03"},
                    "TotalCharges": {"MonetaryValue": "12.30", "CurrencyCode": "USD"},
                }
            }
        }

        first = ups_service.get_rate_for_service(DESTINATION, [{"weight": "2"}], "03")
        second = ups_service.get_rate_for_service(DESTINATION, [{"weight": "2"}], "03")

        self.assertEqual(first, second)
        self.assertEqual(mock_request.call_count, 1)  # second call served from cache

    @patch("apps.shipping.services.ups_service.ups_request")
    def test_different_weight_is_not_a_cache_hit(self, mock_request):
        mock_request.return_value = {
            "RateResponse": {
                "RatedShipment": {
                    "Service": {"Code": "03"},
                    "TotalCharges": {"MonetaryValue": "12.30", "CurrencyCode": "USD"},
                }
            }
        }

        ups_service.get_rate_for_service(DESTINATION, [{"weight": "2"}], "03")
        ups_service.get_rate_for_service(DESTINATION, [{"weight": "9"}], "03")

        self.assertEqual(mock_request.call_count, 2)

    @patch("apps.shipping.services.ups_service.ups_request")
    def test_missing_service_raises(self, mock_request):
        mock_request.return_value = {"RateResponse": {"RatedShipment": []}}

        with self.assertRaises(UPSError):
            ups_service.get_rate_for_service(DESTINATION, [{"weight": "2"}], "03")


@override_settings(**UPS_TEST_SETTINGS)
class UPSTrackingTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("apps.shipping.services.ups_service.ups_request")
    def test_tracking_response_is_flattened(self, mock_request):
        mock_request.return_value = {
            "trackResponse": {
                "shipment": [
                    {
                        "package": [
                            {
                                "trackingNumber": "1Z999AA10123456784",
                                "currentStatus": {"description": "Delivered"},
                                "deliveryDate": [{"date": "20260726"}],
                                "activity": [
                                    {
                                        "status": {"description": "Delivered", "type": "D"},
                                        "date": "20260726",
                                        "time": "101500",
                                        "location": {
                                            "address": {
                                                "city": "Chicago",
                                                "stateProvince": "IL",
                                                "countryCode": "US",
                                            }
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                ]
            }
        }

        result = ups_service.track_shipment("1Z999AA10123456784")

        self.assertEqual(result["tracking_number"], "1Z999AA10123456784")
        self.assertEqual(result["current_status"], "Delivered")
        self.assertEqual(result["delivery_date"], "20260726")
        self.assertEqual(len(result["activities"]), 1)
        self.assertEqual(result["activities"][0]["city"], "Chicago")

    @patch("apps.shipping.services.ups_service.ups_request")
    def test_empty_tracking_payload_raises(self, mock_request):
        mock_request.return_value = {"trackResponse": {"shipment": []}}

        with self.assertRaises(UPSError):
            ups_service.track_shipment("1Z999AA10123456784")


@override_settings(**UPS_TEST_SETTINGS)
class UPSAddressValidationTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("apps.shipping.services.ups_service.ups_request")
    def test_valid_address_returns_candidates(self, mock_request):
        mock_request.return_value = {
            "XAVResponse": {
                "ValidAddressIndicator": "",
                "AddressClassification": {"Code": "2", "Description": "Residential"},
                "Candidate": {
                    "AddressKeyFormat": {
                        "AddressLine": "500 MAIN ST",
                        "PoliticalDivision2": "CHICAGO",
                        "PoliticalDivision1": "IL",
                        "PostcodePrimaryLow": "60601",
                        "CountryCode": "US",
                    }
                },
            }
        }

        result = ups_service.validate_address(DESTINATION)

        self.assertTrue(result["valid"])
        self.assertFalse(result["ambiguous"])
        self.assertEqual(result["classification"], "Residential")
        self.assertEqual(result["candidates"][0]["city"], "CHICAGO")
        self.assertEqual(result["candidates"][0]["address_lines"], ["500 MAIN ST"])

    @patch("apps.shipping.services.ups_service.ups_request")
    def test_unmatched_address_reports_no_candidates(self, mock_request):
        mock_request.return_value = {"XAVResponse": {"NoCandidatesIndicator": ""}}

        result = ups_service.validate_address(DESTINATION)

        self.assertFalse(result["valid"])
        self.assertTrue(result["no_candidates"])
        self.assertEqual(result["candidates"], [])
