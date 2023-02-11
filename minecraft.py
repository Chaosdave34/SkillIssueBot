import requests


def read_json(obj):
    try:
        obj = obj.json()
    except requests.exceptions.JSONDecodeError:
        obj = None
    return obj


class HyixelHandler:
    def __init__(self, key):
        self.key = key
        self.url = "https://api.hypixel.net"

    def get_status(self, uuid):
        response = requests.get(self.url + "/status", params={"key": self.key, "uuid": uuid})
        response = read_json(response)

        response = self.check_response(response)

        return response["session"] if response is not None else None

    def check_response(self, response):
        if not response["success"]:
            raise ApiException(response["cause"])
        return response

    def get_player(self, uuid):
        response = requests.get(self.url + "/player", params={"key": self.key, "uuid": uuid})
        response = read_json(response)

        response = self.check_response(response)

        return response["player"] if response is not None else None

    def get_profiles(self, uuid):
        response = requests.get(self.url + "/skyblock/profiles", params={"key": self.key, "uuid": uuid})
        response = read_json(response)

        response = self.check_response(response)

        return response["profiles"] if response is not None else None


# Mojang API
def username_to_uuid(username):
    response = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{username}")
    response = read_json(response)

    return response["id"] if response is not None else None


def uuid_to_profile(uuid):
    response = requests.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}")

    return read_json(response)


# SkyCrypt
def get_skyblock_profile(playername):
    response = requests.get(f"https://sky.shiiyu.moe/api/v2/profile/{playername}")
    response = read_json(response)
    return response


class ApiException(Exception):
    def __init__(self, message="Api Error"):
        self.message = message
        super().__init__(self.message)
