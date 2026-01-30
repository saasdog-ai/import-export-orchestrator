"""Tests for the centralized entity registry."""

from app.domain.entities import ExportEntity
from app.entities import registry
from app.entities._registry import EntityDefinition, EntityRegistry, FieldDef


class TestEntityRegistryBasics:
    """Test basic registry operations."""

    def test_registry_has_all_entities(self):
        """All four entity types are registered."""
        names = registry.get_names()
        assert set(names) == {"bill", "invoice", "vendor", "project"}

    def test_get_returns_definition(self):
        """get() returns an EntityDefinition for a registered name."""
        defn = registry.get("vendor")
        assert defn is not None
        assert isinstance(defn, EntityDefinition)
        assert defn.name == "vendor"

    def test_get_unknown_returns_none(self):
        """get() returns None for an unregistered name."""
        assert registry.get("nonexistent") is None

    def test_list_all_returns_all(self):
        """list_all() returns every registered definition."""
        all_defs = registry.list_all()
        assert len(all_defs) == 4
        assert all(isinstance(d, EntityDefinition) for d in all_defs)


class TestEntitySchemas:
    """Test that generated schemas match the original hardcoded values."""

    def test_schemas_keys_match(self):
        """Schema dict has all entity names as keys."""
        schemas = registry.get_entity_schemas()
        assert set(schemas.keys()) == {"bill", "invoice", "vendor", "project"}

    def test_bill_schema_fields(self):
        """Bill schema has the expected fields."""
        schemas = registry.get_entity_schemas()
        bill = schemas["bill"]
        field_names = {f.name for f in bill.fields}
        expected = {
            "id",
            "external_id",
            "amount",
            "date",
            "due_date",
            "status",
            "description",
            "currency",
            "vendor_id",
            "project_id",
            "created_at",
            "updated_at",
        }
        assert field_names == expected

    def test_bill_has_vendor_and_project_relationships(self):
        """Bill schema includes vendor and project relationships."""
        schemas = registry.get_entity_schemas()
        bill = schemas["bill"]
        rel_names = {r.name for r in bill.relationships}
        assert rel_names == {"vendor", "project"}

    def test_vendor_schema_fields(self):
        """Vendor schema has the expected fields."""
        schemas = registry.get_entity_schemas()
        vendor = schemas["vendor"]
        field_names = {f.name for f in vendor.fields}
        expected = {
            "id",
            "external_id",
            "name",
            "email",
            "phone",
            "address",
            "created_at",
            "updated_at",
        }
        assert field_names == expected

    def test_project_schema_fields(self):
        """Project schema has the expected fields."""
        schemas = registry.get_entity_schemas()
        project = schemas["project"]
        field_names = {f.name for f in project.fields}
        expected = {
            "id",
            "external_id",
            "code",
            "name",
            "description",
            "status",
            "created_at",
            "updated_at",
        }
        assert field_names == expected

    def test_invoice_schema_fields(self):
        """Invoice schema has the expected fields."""
        schemas = registry.get_entity_schemas()
        invoice = schemas["invoice"]
        field_names = {f.name for f in invoice.fields}
        assert "amount" in field_names
        assert "date" in field_names
        assert "customer_id" in field_names

    def test_required_fields_marked(self):
        """Required fields are marked correctly in the schema."""
        schemas = registry.get_entity_schemas()
        bill = schemas["bill"]
        required = {f.name for f in bill.fields if f.required}
        assert required == {"amount", "date"}


class TestEntityFields:
    """Test that generated ENTITY_FIELDS match the original hardcoded values."""

    def test_entity_fields_keys(self):
        """Entity fields dict has all ExportEntity keys."""
        fields = registry.get_entity_fields()
        assert set(fields.keys()) == {
            ExportEntity.BILL,
            ExportEntity.INVOICE,
            ExportEntity.VENDOR,
            ExportEntity.PROJECT,
        }

    def test_bill_fields_match_original(self):
        """Bill entity fields match the original hardcoded set."""
        fields = registry.get_entity_fields()
        assert fields[ExportEntity.BILL] == {
            "id",
            "external_id",
            "amount",
            "date",
            "due_date",
            "description",
            "currency",
            "vendor_id",
            "project_id",
            "status",
            "created_at",
            "updated_at",
        }

    def test_invoice_fields_include_customer_id(self):
        """Invoice entity fields include customer_id for query compatibility."""
        fields = registry.get_entity_fields()
        assert "customer_id" in fields[ExportEntity.INVOICE]

    def test_vendor_fields_match_original(self):
        """Vendor entity fields match the original hardcoded set."""
        fields = registry.get_entity_fields()
        assert fields[ExportEntity.VENDOR] == {
            "id",
            "external_id",
            "name",
            "email",
            "phone",
            "address",
            "created_at",
            "updated_at",
        }

    def test_project_fields_match_original(self):
        """Project entity fields match the original hardcoded set."""
        fields = registry.get_entity_fields()
        assert fields[ExportEntity.PROJECT] == {
            "id",
            "external_id",
            "code",
            "name",
            "description",
            "status",
            "created_at",
            "updated_at",
        }


class TestNestedFields:
    """Test that generated NESTED_FIELDS match the original hardcoded values."""

    def test_bill_nested_fields(self):
        """Bill nested fields include vendor and project."""
        nested = registry.get_nested_fields()
        bill_nested = nested[ExportEntity.BILL]
        assert "vendor" in bill_nested
        assert "project" in bill_nested
        assert bill_nested["vendor"] == {"id", "name", "email"}
        assert bill_nested["project"] == {"id", "code", "name"}

    def test_invoice_nested_fields(self):
        """Invoice nested fields include vendor and project."""
        nested = registry.get_nested_fields()
        inv_nested = nested[ExportEntity.INVOICE]
        assert "vendor" in inv_nested
        assert "project" in inv_nested
        assert inv_nested["vendor"] == {"id", "name", "email"}
        assert inv_nested["project"] == {"id", "code", "name"}

    def test_vendor_nested_fields(self):
        """Vendor nested fields include project."""
        nested = registry.get_nested_fields()
        assert "project" in nested[ExportEntity.VENDOR]
        assert nested[ExportEntity.VENDOR]["project"] == {"id", "code", "name"}

    def test_project_has_no_nested(self):
        """Project has no nested fields."""
        nested = registry.get_nested_fields()
        assert nested[ExportEntity.PROJECT] == {}


class TestAllowedJoins:
    """Test that generated ALLOWED_JOINS match the original hardcoded values."""

    def test_bill_vendor_join(self):
        """Bill -> vendor join is allowed."""
        joins = registry.get_allowed_joins()
        assert (ExportEntity.BILL, "vendor") in joins
        assert joins[(ExportEntity.BILL, "vendor")] == (ExportEntity.VENDOR, "id")

    def test_bill_project_join(self):
        """Bill -> project join is allowed."""
        joins = registry.get_allowed_joins()
        assert (ExportEntity.BILL, "project") in joins
        assert joins[(ExportEntity.BILL, "project")] == (ExportEntity.PROJECT, "id")

    def test_invoice_vendor_join(self):
        """Invoice -> vendor join is allowed."""
        joins = registry.get_allowed_joins()
        assert (ExportEntity.INVOICE, "vendor") in joins

    def test_invoice_project_join(self):
        """Invoice -> project join is allowed."""
        joins = registry.get_allowed_joins()
        assert (ExportEntity.INVOICE, "project") in joins

    def test_vendor_project_join(self):
        """Vendor -> project join is allowed."""
        joins = registry.get_allowed_joins()
        assert (ExportEntity.VENDOR, "project") in joins

    def test_join_count(self):
        """Exactly 5 joins are defined."""
        joins = registry.get_allowed_joins()
        assert len(joins) == 5


class TestRequiredFields:
    """Test that generated REQUIRED_FIELDS match the original hardcoded values."""

    def test_bill_required(self):
        required = registry.get_required_fields()
        assert required[ExportEntity.BILL] == ["amount", "date"]

    def test_invoice_required(self):
        required = registry.get_required_fields()
        assert required[ExportEntity.INVOICE] == ["amount", "date"]

    def test_vendor_required(self):
        required = registry.get_required_fields()
        assert required[ExportEntity.VENDOR] == ["name"]

    def test_project_required(self):
        required = registry.get_required_fields()
        assert required[ExportEntity.PROJECT] == ["code", "name"]


class TestRegistryIsolation:
    """Test that a fresh registry can be used independently."""

    def test_new_registry_is_empty(self):
        new_reg = EntityRegistry()
        assert new_reg.get_names() == []
        assert new_reg.list_all() == []

    def test_register_custom_entity(self):
        new_reg = EntityRegistry()
        defn = EntityDefinition(
            name="widget",
            label="Widgets",
            description="Test widgets",
            fields=[FieldDef(name="id", type="uuid", label="ID")],
            required_fields=["id"],
        )
        new_reg.register(defn)
        assert new_reg.get("widget") is defn
        assert new_reg.get_names() == ["widget"]
