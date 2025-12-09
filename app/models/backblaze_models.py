from dataclasses import dataclass

@dataclass
class BackblazeAuth:
    api_url: str
    authorization_token: str
    download_url: str

@dataclass
class BackblazeUploadUrl:
    upload_url: str
    authorization_token: str

@dataclass
class BackblazeFile:
    file_id: str
    file_name: str

