import base64
import logging

from core.b24_entity import B24HttpClient

logger = logging.getLogger(__name__)

ROOT_FOLDER_NAME = "Согласования"


class DiskService:
    def __init__(self, client: B24HttpClient):
        self.client = client
        # Per-request in-memory cache so that one approval create
        # doesn't make repeated getlist/getchildren calls for each file.
        self._root_folder_id: str = ""

    # ── Private helpers ────────────────────────────────────────────────────

    def _get_company_storage_id(self) -> str:
        """Return the ID of the company shared storage (ENTITY_TYPE='common')."""
        try:
            result = self.client.call("disk.storage.getlist", {
                "filter": {"ENTITY_TYPE": "common"},
            })
        except RuntimeError as exc:
            err_text = str(exc)
            if "insufficient_scope" in err_text or "higher privileges" in err_text:
                raise RuntimeError(
                    "Disk API requires 'disk' scope. "
                    "Go to Bitrix24 Developer Portal → app settings → add 'disk' to scopes, "
                    "then reinstall the app to obtain a fresh token."
                ) from exc
            raise

        if isinstance(result, list) and result:
            storage_id = str(result[0].get("ID", ""))
            if storage_id:
                logger.debug("[disk] company storage_id=%s", storage_id)
                return storage_id
        raise RuntimeError(
            "Company shared storage not found: "
            "disk.storage.getlist returned no 'common' entries."
        )

    def _get_or_create_root_folder(self, storage_id: str) -> str:
        """Get or create the 'Согласования' root folder in company storage.

        Uses disk.storage.addfolder (requires storage id, not a folder id).
        On DISK_OBJ_22000 (already exists) falls back to searching children.
        """
        try:
            result = self.client.call("disk.storage.addfolder", {
                "id": storage_id,
                "data": {"NAME": ROOT_FOLDER_NAME},
            })
            if isinstance(result, dict):
                folder_id = str(result.get("ID", ""))
                if folder_id:
                    logger.info(
                        "[disk] created root folder '%s' storage_id=%s folder_id=%s",
                        ROOT_FOLDER_NAME, storage_id, folder_id,
                    )
                    return folder_id
        except RuntimeError as exc:
            if "DISK_OBJ_22000" not in str(exc):
                raise
            # Folder already exists — locate it among storage root children.
            logger.debug(
                "[disk] root folder '%s' already exists in storage %s, searching…",
                ROOT_FOLDER_NAME, storage_id,
            )

        children = self.client.call("disk.storage.getchildren", {"id": storage_id})
        if isinstance(children, list):
            for item in children:
                if (
                    isinstance(item, dict)
                    and item.get("NAME") == ROOT_FOLDER_NAME
                    and item.get("TYPE") == "folder"
                ):
                    folder_id = str(item.get("ID", ""))
                    logger.info(
                        "[disk] found existing root folder '%s' folder_id=%s",
                        ROOT_FOLDER_NAME, folder_id,
                    )
                    return folder_id

        raise RuntimeError(
            f"Root folder '{ROOT_FOLDER_NAME}' already exists in company storage "
            f"but was not found in disk.storage.getchildren."
        )

    def _ensure_root_folder(self) -> str:
        """Return (and per-request-cache) the root 'Согласования' folder ID."""
        if not self._root_folder_id:
            storage_id = self._get_company_storage_id()
            self._root_folder_id = self._get_or_create_root_folder(storage_id)
        return self._root_folder_id

    # ── Public API ─────────────────────────────────────────────────────────

    def create_folder(self, folder_name: str) -> str:
        """Create a per-request subfolder inside the 'Согласования' root folder.

        Correct flow:
          1. disk.storage.getlist      → find company 'common' storage
          2. disk.storage.addfolder    → create/find 'Согласования' root folder
          3. disk.folder.addsubfolder  → create per-request subfolder inside it
        """
        root_folder_id = self._ensure_root_folder()
        result = self.client.call("disk.folder.addsubfolder", {
            "id": root_folder_id,
            "data": {"NAME": folder_name},
        })
        if isinstance(result, dict):
            folder_id = str(result.get("ID", ""))
            logger.info("[disk] created request folder '%s' id=%s", folder_name, folder_id)
            return folder_id
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
