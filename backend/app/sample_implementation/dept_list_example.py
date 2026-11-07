from adapter_interface import adapter
from http_client import HTTPClient

class dept_list_crawler(adapter):
    def __init__(self, client):
        self.client = client
    
    def fetch(self):
        pass
    