"""App entry."""
from api import handle_request, handle_checkout
from config import DEBUG
def main():
    print("app start debug=", DEBUG)
