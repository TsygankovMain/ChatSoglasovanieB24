import base64

from core.b24_entity import B24HttpClient


class DiskService:
    def __init__(self, client: B24HttpClient):
        self.client = client

    def create_folder(self, folder_name: str) -> str:
        result = self.client.call("disk.folder.add", {
            "data": {"NAME": folder_name},
        })
        if isinstance(result, dict):
            return str(result.get("ID", ""))
        return str(result)

    def upload_file(self, folder_id: str, filename: str, file_bytes: bytes) -> dict:
        encoded = base64.b64encode(file_bytes).decode("utf-8")
        result = self.client.call("disk.folder.uploadfile", {
            "id": folder_id,
            "data": {"NAME": filename},
            "fileContent": [filename, encoded],
        })
        return result if isinstance(result, dict) else {"ID": str(result)}

    def get_file_url(self, file_id: str) -> str:
        result = self.client.call("disk.file.get", {"id": file_id})
        if isinstance(result, dict):
            return result.get("DOWNLOAD_URL", "")
        return ""
