"""Transaction type names and classification rules (spec 4.2, 4.3)."""

OPENING = "Opening Entry"
MR_CREATED = "MR Created"
MR_ISSUED = "MR Issued"
# Equipment Log Register replaces Asset Movement as the counted document. Asset Movement is
# only shown as a link on the ELR rows, never counted (it would double count).
EQUIPMENT_LOG = "Equipment Log"
ELR_TYPES = ("Issue / Receiving", "Return", "Transfer Receipt")

DEFAULT_EXCLUDED_PURPOSES = (
	"Manufacture",
	"Repack",
	"Material Transfer for Manufacture",
	"Send to Subcontractor",
	"Material Consumption for Manufacture",
)

RECEIVED_TYPES = ("Purchase Receipt", "Material Return", "Petty Cash Receipt", "Other Material Receipt")
ISSUED_TYPES = ("Material Issue", "Supplier Return")
TRANSFERRED_TYPES = ("Stock Transfer",)

# Order of the Transactions by Type chart ties; also the list of known types.
ALL_TYPES = (
	"Purchase Receipt",
	"Material Return",
	"Petty Cash Receipt",
	"Other Material Receipt",
	"Material Issue",
	"Supplier Return",
	"Stock Transfer",
	"Stock Adjustment",
	"Return Request",
	MR_CREATED,
	MR_ISSUED,
	EQUIPMENT_LOG,
)

MR_TYPES = ("Material Issue", "Material Transfer", "Purchase", "Customer Provided")


def classify_stock_entry(row):
	"""Rules are evaluated in spec order; first match wins."""
	if row.is_opening == "Yes":
		return OPENING
	if row.purpose == "Material Receipt":
		if row.ref:
			return "Material Return"
		return "Petty Cash Receipt" if row.petty_cash else "Other Material Receipt"
	if row.purpose == "Material Issue":
		return "Material Issue"
	return "Stock Transfer"
