from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

preset_permissions = {
    "super_admin": ["manage users", "delete extracts",
                    "add extracts", "accounting", "generate pdf", "hr management", "approve extracts", "view edits",
                    "edit extracts"],

    "eng_admin": ["delete extracts", "add extracts", "edit extracts"],
    "acc_admin": ["accounting"],
    "site_manager": ["approve extracts"],
    "engineer": ["add extracts", "delete extracts", "edit extracts"],
    "accountant": ["accounting"]
}