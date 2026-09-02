from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

preset_permissions = {
    "super_admin": ["manage users", "manage page"],
    "eng_admin": [],
    "acc_admin": [],
    "engineer": [],
    "accountant": []
}