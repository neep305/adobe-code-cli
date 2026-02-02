"""Built-in schema templates and template management."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from adobe_experience.schema.models import SchemaTemplate


# Built-in template definitions
BUILTIN_TEMPLATES: Dict[str, SchemaTemplate] = {
    "customer-profile": SchemaTemplate(
        name="customer-profile",
        title="Customer Profile",
        description="Standard customer profile with contact information and demographics",
        domain="customer",
        sample_fields=[
            {"name": "customerId", "type": "string", "required": True, "description": "Unique customer identifier"},
            {"name": "email", "type": "string", "format": "email", "required": True, "description": "Email address"},
            {"name": "firstName", "type": "string", "description": "First name"},
            {"name": "lastName", "type": "string", "description": "Last name"},
            {"name": "phone", "type": "string", "description": "Phone number"},
            {"name": "dateOfBirth", "type": "string", "format": "date", "description": "Date of birth"},
            {"name": "country", "type": "string", "description": "Country code"},
            {"name": "loyaltyTier", "type": "string", "description": "Loyalty program tier"},
            {"name": "createdAt", "type": "string", "format": "date-time", "description": "Account creation date"},
        ],
        tags=["customer", "profile", "b2c"],
        xdm_class="https://ns.adobe.com/xdm/context/profile",
        version="1.0.0",
        created_at=datetime.now(),
    ),
    "product-catalog": SchemaTemplate(
        name="product-catalog",
        title="Product Catalog",
        description="E-commerce product catalog with pricing and inventory",
        domain="product",
        sample_fields=[
            {"name": "productId", "type": "string", "required": True, "description": "Unique product identifier"},
            {"name": "sku", "type": "string", "required": True, "description": "Stock keeping unit"},
            {"name": "name", "type": "string", "required": True, "description": "Product name"},
            {"name": "description", "type": "string", "description": "Product description"},
            {"name": "category", "type": "string", "description": "Product category"},
            {"name": "brand", "type": "string", "description": "Brand name"},
            {"name": "price", "type": "number", "description": "Product price"},
            {"name": "currency", "type": "string", "description": "Currency code (USD, EUR, etc.)"},
            {"name": "stockQuantity", "type": "integer", "description": "Available stock quantity"},
            {"name": "imageUrl", "type": "string", "format": "uri", "description": "Product image URL"},
            {"name": "isActive", "type": "boolean", "description": "Product availability status"},
        ],
        tags=["product", "catalog", "ecommerce"],
        version="1.0.0",
        created_at=datetime.now(),
    ),
    "order-event": SchemaTemplate(
        name="order-event",
        title="Order Event",
        description="E-commerce order/purchase event with transaction details",
        domain="event",
        sample_fields=[
            {"name": "orderId", "type": "string", "required": True, "description": "Unique order identifier"},
            {"name": "customerId", "type": "string", "required": True, "description": "Customer identifier"},
            {"name": "orderDate", "type": "string", "format": "date-time", "required": True, "description": "Order timestamp"},
            {"name": "totalAmount", "type": "number", "required": True, "description": "Total order amount"},
            {"name": "currency", "type": "string", "description": "Currency code"},
            {"name": "status", "type": "string", "description": "Order status (pending, completed, cancelled)"},
            {"name": "paymentMethod", "type": "string", "description": "Payment method used"},
            {"name": "shippingAddress", "type": "object", "description": "Shipping address details"},
            {"name": "items", "type": "array", "description": "Order line items"},
            {"name": "discountCode", "type": "string", "description": "Applied discount code"},
        ],
        tags=["order", "event", "ecommerce", "transaction"],
        xdm_class="https://ns.adobe.com/xdm/context/experienceevent",
        version="1.0.0",
        created_at=datetime.now(),
    ),
}


class TemplateManager:
    """Manage schema templates (built-in and custom)."""

    def __init__(self, templates_dir: Optional[Path] = None):
        """Initialize template manager.

        Args:
            templates_dir: Directory for custom templates. Defaults to ~/.adobe/templates/
        """
        if templates_dir is None:
            templates_dir = Path.home() / ".adobe" / "templates"
        self.templates_dir = templates_dir
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def list_templates(self, include_builtin: bool = True) -> List[SchemaTemplate]:
        """List all available templates.

        Args:
            include_builtin: Include built-in templates

        Returns:
            List of schema templates
        """
        templates = []

        # Add built-in templates
        if include_builtin:
            templates.extend(BUILTIN_TEMPLATES.values())

        # Add custom templates
        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    template = SchemaTemplate(**data)
                    templates.append(template)
            except Exception:
                # Skip invalid templates
                continue

        return templates

    def get_template(self, name: str) -> Optional[SchemaTemplate]:
        """Get template by name.

        Args:
            name: Template name

        Returns:
            Schema template or None if not found
        """
        # Check built-in templates first
        if name in BUILTIN_TEMPLATES:
            return BUILTIN_TEMPLATES[name]

        # Check custom templates
        template_file = self.templates_dir / f"{name}.json"
        if template_file.exists():
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return SchemaTemplate(**data)
            except Exception:
                return None

        return None

    def save_template(self, template: SchemaTemplate, overwrite: bool = False) -> bool:
        """Save custom template.

        Args:
            template: Schema template to save
            overwrite: Allow overwriting existing template

        Returns:
            True if saved successfully
        """
        # Prevent overwriting built-in templates
        if template.name in BUILTIN_TEMPLATES:
            raise ValueError(f"Cannot overwrite built-in template: {template.name}")

        template_file = self.templates_dir / f"{template.name}.json"

        if template_file.exists() and not overwrite:
            raise FileExistsError(f"Template already exists: {template.name}")

        try:
            with open(template_file, "w", encoding="utf-8") as f:
                # Convert datetime to ISO format for JSON serialization
                data = template.model_dump(mode="json")
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def delete_template(self, name: str) -> bool:
        """Delete custom template.

        Args:
            name: Template name

        Returns:
            True if deleted successfully
        """
        # Prevent deleting built-in templates
        if name in BUILTIN_TEMPLATES:
            raise ValueError(f"Cannot delete built-in template: {name}")

        template_file = self.templates_dir / f"{name}.json"

        if not template_file.exists():
            return False

        try:
            template_file.unlink()
            return True
        except Exception:
            return False

    def template_exists(self, name: str) -> bool:
        """Check if template exists.

        Args:
            name: Template name

        Returns:
            True if template exists
        """
        return self.get_template(name) is not None
