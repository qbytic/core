class CredManager:
    user: str = None
    is_admin: bool = False
    access_token: dict = None

    def __init__(self, access_token=None):
        self.access_token = access_token or {}
        self.user = self.access_token.get("user")
        self.is_admin = self.access_token.get("is_admin")

