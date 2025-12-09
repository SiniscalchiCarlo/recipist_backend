import base64
import json
import logging
import requests
import uuid
from pathlib import Path
from typing import List
from app.core.config import settings
from app.models.backblaze_models import (
    BackblazeAuth,
    BackblazeUploadUrl,
    BackblazeFile,
)


class BackblazeConfig:
    """
    Holds Backblaze B2 configuration values loaded from environment variables.

    Attributes
    ----------
    application_key_id : str
        B2 Application Key ID.
    application_key : str
        B2 Application Key.
    bucket_id : str
        Backblaze bucket ID.
    bucket_name : str
        Backblaze bucket name.
    """

    def __init__(self):
        self.application_key_id = settings.b2_application_key_id
        self.application_key = settings.b2_application_key
        self.bucket_id = settings.b2_bucket_id
        self.bucket_name = settings.b2_bucket_name

    @property
    def is_valid(self) -> bool:
        """
        Returns True if all required Backblaze configuration fields are non-empty.
        NOTE: This does NOT validate that the credentials are correct on Backblaze.

        Returns
        -------
        bool
            True if all config values are present, False otherwise.
        """
        return all([
            self.application_key_id,
            self.application_key,
            self.bucket_id,
            self.bucket_name,
        ])


class BackblazeStorageService:
    """
    Service class responsible for:
    - Authorizing with Backblaze B2
    - Uploading files
    - Listing files by prefix
    - Deleting files or files under a prefix

    Parameters
    ----------
    enable_logging : bool, optional
        Whether to enable console logging for debugging.
    """

    def __init__(self, enable_logging=False):
        self.config = BackblazeConfig()
        self.logger = logging.getLogger("Backblaze")
        self.logger.setLevel(logging.INFO if enable_logging else logging.CRITICAL)

    def _log(self, msg: str):
        """Internal helper to print logs only when logging is enabled."""
        self.logger.info(msg)

    # -------------------------
    # AUTHORIZATION
    # -------------------------
    def authorize(self) -> BackblazeAuth:
        """
        Authorizes the Backblaze B2 account and retrieves an authorization token.

        Returns
        -------
        BackblazeAuth
            Contains API URL, authorization token, and download URL.

        Raises
        ------
        RuntimeError
            If configuration is incomplete or the API request fails.
        """
        if not self.config.is_valid:
            raise RuntimeError("Backblaze configuration is incomplete")

        credentials = base64.b64encode(
            f"{self.config.application_key_id}:{self.config.application_key}".encode()
        ).decode()

        url = "https://api.backblazeb2.com/b2api/v2/b2_authorize_account"
        headers = {"Authorization": f"Basic {credentials}"}

        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            raise RuntimeError(f"Authorization failed: {res.text}")

        data = res.json()
        return BackblazeAuth(
            api_url=data["apiUrl"],
            authorization_token=data["authorizationToken"],
            download_url=data["downloadUrl"],
        )

    # -------------------------
    # GET UPLOAD URL
    # -------------------------
    def get_upload_url(self, auth: BackblazeAuth) -> BackblazeUploadUrl:
        """
        Requests a Backblaze upload URL specific to the configured bucket.

        Parameters
        ----------
        auth : BackblazeAuth
            Authorization metadata containing token and API base URL.

        Returns
        -------
        BackblazeUploadUrl
            Contains the upload URL and upload authorization token.

        Raises
        ------
        RuntimeError
            If the Backblaze API returns an error.
        """
        url = f"{auth.api_url}/b2api/v2/b2_get_upload_url"
        payload = {"bucketId": self.config.bucket_id}

        res = requests.post(url, headers={"Authorization": auth.authorization_token},
                            json=payload)

        if res.status_code != 200:
            raise RuntimeError(f"Upload URL failed: {res.text}")

        data = res.json()
        return BackblazeUploadUrl(
            upload_url=data["uploadUrl"],
            authorization_token=data["authorizationToken"]
        )

    # -------------------------
    # UPLOAD FILE
    # -------------------------
    def upload_file(self, file_path: Path, storage_path: str) -> str:
        """
        Uploads a file to Backblaze B2 under a given storage path.

        Parameters
        ----------
        file_path : Path
            Local file path to upload.
        storage_path : str
            Folder/prefix inside the B2 bucket (e.g. "recipe_steps/123").

        Returns
        -------
        str
            Full download URL of the uploaded file.

        Raises
        ------
        RuntimeError
            If configuration is invalid or upload fails.
        """
        if not self.config.is_valid:
            raise RuntimeError("Backblaze config incomplete")

        auth = self.authorize()
        upload = self.get_upload_url(auth)

        file_bytes = file_path.read_bytes()
        extension = file_path.suffix or ".jpg"
        unique_name = f"{uuid.uuid4()}{extension}"
        encoded_path = self._encode(f"{storage_path}/{unique_name}")

        headers = {
            "Authorization": upload.authorization_token,
            "X-Bz-File-Name": encoded_path,
            "Content-Type": "b2/x-auto",
            "X-Bz-Content-Sha1": "do_not_verify",
            "Content-Length": str(len(file_bytes)),
        }

        res = requests.post(upload.upload_url, headers=headers, data=file_bytes)

        if res.status_code != 200:
            raise RuntimeError(f"Upload failed: {res.text}")

        file_name = res.json().get("fileName")
        return f"{auth.download_url}/file/{self.config.bucket_name}/{file_name}"

    # -------------------------
    # LIST FILES BY PREFIX
    # -------------------------
    def list_files(self, auth: BackblazeAuth, prefix: str) -> List[BackblazeFile]:
        """
        Lists all files in the Backblaze bucket that start with a given prefix.
        Uses paging internally until all file names are retrieved.

        Parameters
        ----------
        auth : BackblazeAuth
            Authorization metadata for API requests.
        prefix : str
            Bucket prefix (folder path) to search under.

        Returns
        -------
        List[BackblazeFile]
            A list of files found under the prefix.

        Raises
        ------
        RuntimeError
            If Backblaze returns an error.
        """
        url = f"{auth.api_url}/b2api/v2/b2_list_file_names"
        files = []
        start_name = None

        while True:
            payload = {
                "bucketId": self.config.bucket_id,
                "maxFileCount": 1000,
                "prefix": prefix,
            }
            if start_name:
                payload["startFileName"] = start_name

            res = requests.post(url,
                                headers={"Authorization": auth.authorization_token},
                                json=payload)

            if res.status_code != 200:
                raise RuntimeError(f"File listing failed: {res.text}")

            data = res.json()
            for item in data.get("files", []):
                files.append(BackblazeFile(
                    file_id=item["fileId"],
                    file_name=item["fileName"]
                ))

            start_name = data.get("nextFileName")
            if not start_name:
                break

        return files

    # -------------------------
    # DELETE FILE
    # -------------------------
    def delete_file(self, auth: BackblazeAuth, f: BackblazeFile):
        """
        Deletes a specific Backblaze B2 file version (file name + file ID).

        Parameters
        ----------
        auth : BackblazeAuth
            Authorization metadata.
        f : BackblazeFile
            File to delete (name + ID).

        Raises
        ------
        RuntimeError
            If deletion fails.
        """
        url = f"{auth.api_url}/b2api/v2/b2_delete_file_version"
        payload = {
            "fileName": f.file_name,
            "fileId": f.file_id
        }
        res = requests.post(url,
                            headers={"Authorization": auth.authorization_token},
                            json=payload)
        if res.status_code != 200:
            raise RuntimeError(f"Delete failed: {res.text}")

    # -------------------------
    # DELETE FILES BY PREFIX
    # -------------------------
    def delete_prefix(self, prefix: str):
        """
        Deletes ALL files in Backblaze B2 whose names begin with the given prefix.

        Parameters
        ----------
        prefix : str
            The folder/path prefix (e.g. "recipe_cover/123").

        Notes
        -----
        This calls:
            - authorize()
            - list_files()
            - delete_file() for each result
        """
        auth = self.authorize()
        encoded = self._encode(prefix)
        files = self.list_files(auth, encoded)

        for f in files:
            self.delete_file(auth, f)

    # -------------------------
    # ENCODING
    # -------------------------
    def _encode(self, path: str) -> str:
        """
        Encodes each segment of a file path so it can be safely used in B2 headers.

        Parameters
        ----------
        path : str
            File path or prefix (e.g. "recipe_steps/123/file.jpg").

        Returns
        -------
        str
            URL-encoded path string.
        """
        return "/".join([requests.utils.quote(seg) for seg in path.split("/") if seg])

