"""Faker integration strategies for realistic data generation."""

import logging
import random
from typing import Any, Dict, Optional

from faker import Faker

from adobe_experience.schema.models import XDMDataType, XDMFieldFormat

logger = logging.getLogger(__name__)


class FakerStrategy:
    """Strategy for mapping XDM types to Faker providers."""

    # Field name patterns → Faker provider mappings
    FIELD_NAME_MAPPING = {
        # Personal info
        "first_name": "first_name",
        "last_name": "last_name",
        "full_name": "name",
        "name": "name",
        "username": "user_name",
        "email": "email",
        "password": "password",
        # Contact
        "phone": "phone_number",
        "phone_number": "phone_number",
        "mobile": "phone_number",
        "mobile_phone": "phone_number",
        # Address
        "street": "street_address",
        "street_address": "street_address",
        "address": "address",
        "city": "city",
        "state": "state",
        "state_abbr": "state_abbr",
        "country": "country",
        "country_code": "country_code",
        "postal_code": "postcode",
        "zip": "postcode",
        "zip_code": "postcode",
        # Identifiers
        "ssn": "ssn",
        "uuid": "uuid4",
        "guid": "uuid4",
        "ein": "ein",
        # Internet
        "url": "url",
        "domain": "domain_name",
        "ipv4": "ipv4",
        "ipv6": "ipv6",
        "mac_address": "mac_address",
        "user_agent": "user_agent",
        # Company
        "company": "company",
        "company_name": "company",
        "job_title": "job",
        "job": "job",
        # Financial
        "credit_card": "credit_card_number",
        "credit_card_number": "credit_card_number",
        "iban": "iban",
        "bic": "bic",
        "currency": "currency_code",
        # Dates
        "birth_date": "date_of_birth",
        "date_of_birth": "date_of_birth",
        "dob": "date_of_birth",
        "created_at": "date_time_between:start_date=-1y",
        "updated_at": "date_time_between:start_date=-30d",
        "registered_at": "date_time_between:start_date=-2y",
        # Content
        "title": "sentence:nb_words=4",
        "description": "text:max_nb_chars=200",
        "comment": "text:max_nb_chars=500",
        "bio": "text:max_nb_chars=300",
        # Product
        "product_name": "catch_phrase",
        "sku": "ean13",
        "barcode": "ean13",
        "category": "word",
        # Location
        "latitude": "latitude",
        "longitude": "longitude",
        "timezone": "timezone",
    }

    TYPE_DEFAULT_MAPPING = {
        XDMDataType.STRING: "word",
        XDMDataType.INTEGER: "random_int:min=0:max=1000",
        XDMDataType.NUMBER: "pydecimal:left_digits=5:right_digits=2:positive=True",
        XDMDataType.BOOLEAN: "boolean",
        XDMDataType.DATE: "date_between:start_date=-1y",
        XDMDataType.DATE_TIME: "date_time_between:start_date=-1y",
    }

    FORMAT_MAPPING = {
        XDMFieldFormat.EMAIL: "email",
        XDMFieldFormat.URI: "url",
        XDMFieldFormat.UUID: "uuid4",
        XDMFieldFormat.DATE: "date_between:start_date=-1y",
        XDMFieldFormat.DATE_TIME: "date_time_between:start_date=-1y",
    }

    @staticmethod
    def infer_faker_provider(
        field_name: str,
        xdm_type: XDMDataType,
        xdm_format: Optional[XDMFieldFormat] = None,
    ) -> str:
        """Infer Faker provider from field name and type.

        Args:
            field_name: Field name
            xdm_type: XDM data type
            xdm_format: Optional XDM format

        Returns:
            Faker provider string (e.g., "name", "email", "date_time_between:start_date=-1y")

        Examples:
            >>> FakerStrategy.infer_faker_provider("email", XDMDataType.STRING)
            'email'
            >>> FakerStrategy.infer_faker_provider("price", XDMDataType.NUMBER)
            'pydecimal:left_digits=5:right_digits=2:positive=True'
        """
        field_lower = field_name.lower()

        # 1. Check format first (most specific)
        if xdm_format and xdm_format in FakerStrategy.FORMAT_MAPPING:
            return FakerStrategy.FORMAT_MAPPING[xdm_format]

        # 2. Exact field name match
        if field_lower in FakerStrategy.FIELD_NAME_MAPPING:
            return FakerStrategy.FIELD_NAME_MAPPING[field_lower]

        # 3. Pattern matching (contains)
        for pattern, provider in FakerStrategy.FIELD_NAME_MAPPING.items():
            if pattern in field_lower:
                return provider

        # 4. Special patterns
        if "email" in field_lower:
            return "email"
        if "phone" in field_lower or "mobile" in field_lower:
            return "phone_number"
        if "address" in field_lower:
            return "address"
        if "date" in field_lower or "time" in field_lower:
            if xdm_type == XDMDataType.DATE or xdm_format == XDMFieldFormat.DATE:
                return "date_between:start_date=-1y"
            return "date_time_between:start_date=-1y"
        if "price" in field_lower or "amount" in field_lower or "value" in field_lower:
            return "pydecimal:left_digits=5:right_digits=2:positive=True"
        if "quantity" in field_lower or "count" in field_lower:
            return "random_int:min=1:max=100"
        if "status" in field_lower or "state" in field_lower:
            # Will use enum if available
            return "word"
        if "url" in field_lower or "link" in field_lower:
            return "url"
        if "code" in field_lower:
            return "bothify:text=???-###"

        # 5. Fallback to type default
        return FakerStrategy.TYPE_DEFAULT_MAPPING.get(xdm_type, "word")


class FakerFactory:
    """Factory for creating and caching Faker instances."""

    def __init__(self):
        """Initialize Faker factory."""
        self._fakers: Dict[str, Faker] = {}

    def get_faker(self, locale: str = "en_US") -> Faker:
        """Get or create Faker instance for locale.

        Args:
            locale: Locale code (e.g., "en_US", "ko_KR", "ja_JP")

        Returns:
            Faker instance
        """
        if locale not in self._fakers:
            self._fakers[locale] = Faker(locale)
        return self._fakers[locale]

    def generate_value(
        self,
        provider: str,
        locale: str = "en_US",
        xdm_type: Optional[XDMDataType] = None,
    ) -> Any:
        """Generate value using Faker provider.

        Args:
            provider: Faker provider string (e.g., "name", "random_int:min=0:max=100")
            locale: Locale code
            xdm_type: Optional XDM type for type coercion

        Returns:
            Generated value

        Examples:
            >>> factory = FakerFactory()
            >>> factory.generate_value("name")
            'John Doe'
            >>> factory.generate_value("random_int:min=0:max=100")
            42
        """
        faker = self.get_faker(locale)

        # Parse provider string (format: "provider:arg1=val1:arg2=val2")
        parts = provider.split(":")
        provider_name = parts[0]
        kwargs = {}

        # Parse arguments
        for part in parts[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                # Try to convert to appropriate type
                if value.lower() == "true":
                    kwargs[key] = True
                elif value.lower() == "false":
                    kwargs[key] = False
                elif value.isdigit():
                    kwargs[key] = int(value)
                elif value.replace(".", "").replace("-", "").isdigit():
                    kwargs[key] = float(value)
                else:
                    kwargs[key] = value

        try:
            # Get provider method
            if hasattr(faker, provider_name):
                method = getattr(faker, provider_name)
                value = method(**kwargs) if kwargs else method()
            else:
                logger.warning(f"Unknown Faker provider: {provider_name}, using 'word'")
                value = faker.word()

            # Type coercion
            if xdm_type:
                if xdm_type == XDMDataType.STRING and not isinstance(value, str):
                    value = str(value)
                elif xdm_type == XDMDataType.INTEGER and not isinstance(value, int):
                    value = int(float(value)) if isinstance(value, (int, float, str)) else 0
                elif xdm_type == XDMDataType.NUMBER and not isinstance(value, (int, float)):
                    value = float(value) if isinstance(value, (int, float, str)) else 0.0

            return value

        except Exception as e:
            logger.error(f"Error generating value with provider '{provider}': {e}")
            # Fallback to simple default
            if xdm_type == XDMDataType.STRING:
                return faker.word()
            elif xdm_type == XDMDataType.INTEGER:
                return random.randint(0, 1000)
            elif xdm_type == XDMDataType.NUMBER:
                return round(random.uniform(0, 1000), 2)
            elif xdm_type == XDMDataType.BOOLEAN:
                return random.choice([True, False])
            else:
                return faker.word()
