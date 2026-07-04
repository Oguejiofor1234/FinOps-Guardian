import pathlib


def load_expense_policy() -> str:
    """Helper function to load the corporate expense policy guidelines."""
    policy_path = pathlib.Path(__file__).parent / "expense_policy.md"
    try:
        return policy_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "Expense policy guidelines are currently unavailable."
