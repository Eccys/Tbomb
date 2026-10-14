import copy
import json
from pathlib import Path
import threading
import time
import requests


class APIProvider:

    api_providers = []
    delay = 0
    status = True

    def __init__(self, cc, target, mode, delay=0):
        api_path = Path(__file__).resolve().parent.parent / 'apidata.json'
        try:
            with open(api_path, 'r', encoding='utf-8') as f:
                PROVIDERS = json.load(f)
        except Exception:
            PROVIDERS = requests.get(
                "https://github.com/TheSpeedX/TBomb/raw/master/apidata.json",
                timeout=15,
            ).json()
        self.config = None
        self.cc = cc
        self.target = target
        self.mode = mode
        self.index = -1
        self.lock = threading.Lock()
        self.api_version = PROVIDERS.get("version", "2")
        APIProvider.delay = delay
        APIProvider.status = True
        providers = PROVIDERS.get(mode.lower(), {})
        APIProvider.api_providers = copy.deepcopy(list(providers.get(cc, [])))
        if len(APIProvider.api_providers) < 10:
            APIProvider.api_providers += copy.deepcopy(list(providers.get("multi", [])))

    def format(self):
        config_dump = json.dumps(self.config)
        config_dump = config_dump.replace("{target}", self.target)
        config_dump = config_dump.replace("{cc}", self.cc)
        self.config = json.loads(config_dump)

    def select_api(self):
        try:
            if len(APIProvider.api_providers) == 0:
                raise IndexError
            self.index += 1
            if self.index >= len(APIProvider.api_providers):
                self.index = 0
        except IndexError:
            self.index = -1
            self.config = None
            return
        self.config = copy.deepcopy(APIProvider.api_providers[self.index])
        perma_headers = {"User-Agent":
                         "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:72.0)"
                         " Gecko/20100101 Firefox/72.0"}
        if "headers" in self.config:
            self.config["headers"].update(perma_headers)
        else:
            self.config["headers"] = perma_headers
        self.format()

    def remove(self):
        try:
            del APIProvider.api_providers[self.index]
            self.index -= 1
            return True
        except Exception:
            return False

    def request(self):
        self.select_api()
        if not self.config or self.index == -1:
            return None
        identifier = self.config.pop("identifier", "").lower()
        self.config.pop('name', None)
        self.config['timeout'] = 30
        try:
            response = requests.request(**self.config)
            return identifier in response.text.lower()
        except Exception:
            return False

    def hit(self):
        if not APIProvider.status:
            return None
        try:
            time.sleep(APIProvider.delay)
            with self.lock:
                if not APIProvider.status:
                    return None
                response = self.request()
                if response is False:
                    self.remove()
                elif response is None:
                    APIProvider.status = False
                return response
        except Exception:
            return False

