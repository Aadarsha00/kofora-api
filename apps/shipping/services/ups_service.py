"""Business-level UPS operations: live rates, tracking, and address validation.

Every call here is non-billable. Creating shipments and buying labels is a
separate, billable surface and is deliberately not implemented.
"""

from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.cache import cache

from .ups_client import UPSError, ups_request

RATING_PATH = "/api/rating/v2409/{request_option}"
TRACKING_PATH = "/api/track/v1/details/{tracking_number}"
ADDRESS_VALIDATION_PATH = "/api/addressvalidation/v2/{request_option}"

SERVICE_NAMES = {
    "01": "UPS Next Day Air",
    "02": "UPS 2nd Day Air",
    "03": "UPS Ground",
    "07": "UPS Worldwide Express",
    "08": "UPS Worldwide Expedited",
    "11": "UPS Standard",
    "12": "UPS 3 Day Select",
    "13": "UPS Next Day Air Saver",
    "14": "UPS Next Day Air Early",
    "54": "UPS Worldwide Express Plus",
    "59": "UPS 2nd Day Air A.M.",
    "65": "UPS Worldwide Saver",
}


def _as_list(value):
    """UPS collapses single-element arrays into bare objects."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _shipper_address():
    return {
        "AddressLine": [settings.UPS_SHIPPER_ADDRESS_LINE],
        "City": settings.UPS_SHIPPER_CITY,
        "StateProvinceCode": settings.UPS_SHIPPER_STATE,
        "PostalCode": settings.UPS_SHIPPER_POSTAL_CODE,
        "CountryCode": settings.UPS_SHIPPER_COUNTRY,
    }


def _destination_address(destination):
    lines = [destination.get("address_line_1") or ""]
    if destination.get("address_line_2"):
        lines.append(destination["address_line_2"])
    return {
        "AddressLine": lines,
        "City": destination.get("city") or "",
        "StateProvinceCode": destination.get("state_province") or "",
        "PostalCode": destination.get("postal_code") or "",
        "CountryCode": destination.get("country") or "",
    }


def _build_packages(packages):
    built = []
    for package in packages:
        entry = {
            "PackagingType": {"Code": "02"},  # customer-supplied packaging
            "PackageWeight": {
                "UnitOfMeasurement": {"Code": settings.UPS_WEIGHT_UNIT},
                "Weight": str(package["weight"]),
            },
        }
        if all(package.get(dim) for dim in ("length", "width", "height")):
            entry["Dimensions"] = {
                "UnitOfMeasurement": {"Code": settings.UPS_DIMENSION_UNIT},
                "Length": str(package["length"]),
                "Width": str(package["width"]),
                "Height": str(package["height"]),
            }
        built.append(entry)
    return built


def _normalize_rate(rated_shipment):
    service_code = (rated_shipment.get("Service") or {}).get("Code", "")
    total = rated_shipment.get("TotalCharges") or {}
    negotiated = (
        (rated_shipment.get("NegotiatedRateCharges") or {}).get("TotalCharge") or {}
    )
    guaranteed = (rated_shipment.get("GuaranteedDelivery") or {}).get(
        "BusinessDaysInTransit"
    )
    published_charge = _to_decimal(total.get("MonetaryValue"))
    negotiated_charge = _to_decimal(negotiated.get("MonetaryValue"))
    return {
        "service_code": service_code,
        "service_name": SERVICE_NAMES.get(service_code, f"UPS service {service_code}"),
        "published_charge": published_charge,
        "negotiated_charge": negotiated_charge,
        # What the merchant actually pays, when an account number unlocks it.
        "total_charge": negotiated_charge or published_charge,
        "currency": total.get("CurrencyCode") or settings.DEFAULT_CURRENCY,
        "business_days_in_transit": guaranteed,
    }


def get_rates(destination, packages, request_option="Shop", service_code=None):
    """Fetch live UPS rates for a destination.

    `Shop` returns every available service; `Rate` prices a single `service_code`.
    """
    if not packages:
        raise UPSError("At least one package is required to request rates")

    shipment = {
        "Shipper": {
            "Name": settings.UPS_SHIPPER_NAME,
            "Address": _shipper_address(),
        },
        "ShipFrom": {
            "Name": settings.UPS_SHIPPER_NAME,
            "Address": _shipper_address(),
        },
        "ShipTo": {
            "Name": destination.get("full_name") or "Customer",
            "Address": _destination_address(destination),
        },
        "Package": _build_packages(packages),
    }

    # The account number is what makes UPS return negotiated rates at all.
    if settings.UPS_ACCOUNT_NUMBER:
        shipment["Shipper"]["ShipperNumber"] = settings.UPS_ACCOUNT_NUMBER
        shipment["ShipmentRatingOptions"] = {"NegotiatedRatesIndicator": "Y"}

    if request_option == "Rate":
        if not service_code:
            raise UPSError("service_code is required when request_option is 'Rate'")
        shipment["Service"] = {"Code": service_code}

    body = {
        "RateRequest": {
            "Request": {"RequestOption": request_option},
            "Shipment": shipment,
        }
    }

    payload = ups_request(
        "POST", RATING_PATH.format(request_option=request_option), json_body=body
    )
    rated = _as_list((payload.get("RateResponse") or {}).get("RatedShipment"))
    rates = [_normalize_rate(item) for item in rated]
    return sorted(
        rates, key=lambda r: r["total_charge"] if r["total_charge"] is not None else Decimal("9999999")
    )


def get_rate_for_service(destination, packages, service_code):
    """Return the live UPS charge (Decimal) for a single service, cached.

    This is the checkout hot path: it runs on every cart total, so the result
    is cached by destination + weight + service. Raises UPSError if UPS prices
    nothing for the service, letting the caller fall back to a flat rate.
    """
    total_weight = sum(
        (_to_decimal(p.get("weight")) or Decimal("0")) for p in packages
    )
    postal = (destination.get("postal_code") or "").strip().upper()
    country = (destination.get("country") or "").strip().upper()
    cache_key = f"ups:rate:{service_code}:{country}:{postal}:{total_weight}"

    cached = cache.get(cache_key)
    if cached is not None:
        return Decimal(cached)

    rates = get_rates(
        destination, packages, request_option="Rate", service_code=service_code
    )
    match = next((r for r in rates if r["service_code"] == service_code), None)
    if not match or match["total_charge"] is None:
        raise UPSError(f"UPS returned no rate for service {service_code}")

    charge = match["total_charge"]
    cache.set(cache_key, str(charge), settings.UPS_RATE_CACHE_SECONDS)
    return charge


def track_shipment(tracking_number):
    payload = ups_request(
        "GET",
        TRACKING_PATH.format(tracking_number=tracking_number),
        params={"locale": "en_US", "returnSignature": "false"},
    )
    shipments = _as_list((payload.get("trackResponse") or {}).get("shipment"))
    if not shipments:
        raise UPSError(f"UPS returned no tracking data for {tracking_number}")

    packages = _as_list(shipments[0].get("package"))
    if not packages:
        raise UPSError(f"UPS returned no package detail for {tracking_number}")

    package = packages[0]
    activities = []
    for activity in _as_list(package.get("activity")):
        location = (activity.get("location") or {}).get("address") or {}
        status = activity.get("status") or {}
        activities.append(
            {
                "status": status.get("description", ""),
                "status_type": status.get("type", ""),
                "date": activity.get("date", ""),
                "time": activity.get("time", ""),
                "city": location.get("city", ""),
                "state": location.get("stateProvince", ""),
                "country": location.get("countryCode", ""),
            }
        )

    delivery_dates = _as_list(package.get("deliveryDate"))
    current_status = (package.get("currentStatus") or {}).get("description", "")
    return {
        "tracking_number": package.get("trackingNumber", tracking_number),
        "current_status": current_status or (activities[0]["status"] if activities else ""),
        "delivery_date": delivery_dates[0].get("date", "") if delivery_dates else "",
        "activities": activities,
    }


def validate_address(address):
    """Classify and validate a destination address (request option 3 = both)."""
    body = {
        "XAVRequest": {
            "AddressKeyFormat": {
                "AddressLine": _destination_address(address)["AddressLine"],
                "PoliticalDivision2": address.get("city") or "",
                "PoliticalDivision1": address.get("state_province") or "",
                "PostcodePrimaryLow": address.get("postal_code") or "",
                "CountryCode": address.get("country") or "",
            }
        }
    }

    payload = ups_request(
        "POST", ADDRESS_VALIDATION_PATH.format(request_option="3"), json_body=body
    )
    response = payload.get("XAVResponse") or {}

    candidates = []
    for candidate in _as_list(response.get("Candidate")):
        key_format = candidate.get("AddressKeyFormat") or {}
        candidates.append(
            {
                "address_lines": _as_list(key_format.get("AddressLine")),
                "city": key_format.get("PoliticalDivision2", ""),
                "state_province": key_format.get("PoliticalDivision1", ""),
                "postal_code": key_format.get("PostcodePrimaryLow", ""),
                "country": key_format.get("CountryCode", ""),
            }
        )

    classification = response.get("AddressClassification") or {}
    return {
        "valid": "ValidAddressIndicator" in response,
        "ambiguous": "AmbiguousAddressIndicator" in response,
        "no_candidates": "NoCandidatesIndicator" in response,
        "classification": classification.get("Description", ""),
        "candidates": candidates,
    }
