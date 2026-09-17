from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

preset_permissions = {
    "super_admin": ["manage users", "manage page", "extracts history", "edit extracts", "delete extracts", "add extracts", "accounting", "generate pdf"],
    "eng_admin": ["extracts history", "edit extracts", "delete extracts", "add extracts", "generate pdf"],
    "acc_admin": ["accounting", "generate pdf"],
    "site_manager": ["approve extracts"],
    "engineer": [],
    "accountant": []
}