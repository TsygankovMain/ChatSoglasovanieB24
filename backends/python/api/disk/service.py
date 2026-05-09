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
                logger.info("[disk] company storage_id=%s", storage_id)
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
            logger.info(
                "[disk] root folder '%s' already exists in storage %s, searching…",
                ROOT_FOLDER_NAME, storage_id,
            )

        children = self.client.call("disk.storage.getchildren", {"id": storage_id})
        if isinstance(children, list):
            logger.info(
                "[disk] getchildren returned %s items for storage_id=%s",
                len(children), storage_id,
            )
            for item in children:
                if not isinstance(item, dict):
                    continue
                item_name = item.get("NAME", "")
                item_type = str(item.get("TYPE", "")).lower()
                item_id = str(item.get("ID", ""))
                logger.debug("[disk] getchildren item name=%r type=%r id=%s", item_name, item_type, item_id)
                if item_name == ROOT_FOLDER_NAME and item_type == "folder":
                    logger.info(
                        "[disk] found existing root folder '%s' folder_id=%s",
                        ROOT_FOLDER_NAME, item_id,
                    )
                    return item_id
        else:
            logger.warning("[disk] getchildren returned non-list type=%r", type(children).__name__)

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

    def _absolute_portal_url(self, url: str) -> str:
        value = str(url or "").strip()
        if not value:
            return ""
        if value.startswith(("https://", "http://")):
            return value
        if value.startswith("/"):
            return f"https://{self.client.account.domain_url}{value}"
        return value

    def get_folder_files(self, folder_id: str) -> list[dict]:
        """Return [{id, name, url}] for every file in the given folder.

        Uses a single disk.folder.getchildren call — more efficient than
        calling disk.file.get for each file ID individually.
        Returns an empty list on any error (non-critical, degrades gracefully).
        """
        if not folder_id:
            return []
        try:
            children = self.client.call("disk.folder.getchildren", {"id": folder_id})
        except RuntimeError:
            logger.warning("[disk] get_folder_files failed for folder_id=%s", folder_id)
            return []

        files = []
        if isinstance(children, list):
            for item in children:
                if not isinstance(item, dict):
                    continue
                if str(item.get("TYPE", "")).lower() != "file":
                    continue
                # Prefer DETAIL_URL so user opens the file in Bitrix24 UI
                # instead of forcing browser download from DOWNLOAD_URL.
                view_url = self._absolute_portal_url(str(item.get("DETAIL_URL", "")))
                if not view_url:
                    view_url = self._absolute_portal_url(str(item.get("DOWNLOAD_URL", "")))
                files.append({
                    "id": str(item.get("ID", "")),
                    "name": str(item.get("NAME", "")),
                    "url": view_url,
                })
        logger.debug("[disk] get_folder_files folder_id=%s count=%s", folder_id, len(files))
        return files

    def get_file_url(self, file_id: str) -> str:
        result = self.client.call("disk.file.get", {"id": file_id})
        if isinstance(result, dict):
            return (
                self._absolute_portal_url(str(result.get("DETAIL_URL", "")))
                or self._absolute_portal_url(str(result.get("DOWNLOAD_URL", "")))
            )
        return ""
