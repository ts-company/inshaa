from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

preset_permissions = {
    "super_admin": ["manage users", "manage page", "manage extracts"],
    "eng_admin": ["manage extracts"],
    "acc_admin": ["manage extracts"],
    "site_manager": ["approve extracts"],
    "engineer": [],
    "accountant": []
}