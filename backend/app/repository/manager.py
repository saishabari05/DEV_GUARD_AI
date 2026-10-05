from .workspace import (
    clone_git_repository,
    extract_zip_repository,
    resolve_workspace_path,
    create_repository_zip,
    clean_workspace
)
from .detector import detect_repository_metadata

class RepositoryManager:
    @staticmethod
    def ingest_git_repo(git_url: str) -> dict:
        ws_id, ws_path = clone_git_repository(git_url)
        metadata = detect_repository_metadata(ws_path)
        metadata["repository_url"] = git_url
        repo_name = git_url.rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        if repo_name:
            metadata["repository_name"] = repo_name
        return {
            "workspace_id": ws_id,
            "source_type": "git",
            "git_url": git_url,
            "metadata": metadata
        }

    @staticmethod
    def ingest_zip_repo(zip_bytes: bytes) -> dict:
        ws_id, ws_path = extract_zip_repository(zip_bytes)
        metadata = detect_repository_metadata(ws_path)
        return {
            "workspace_id": ws_id,
            "source_type": "zip",
            "metadata": metadata
        }

    @staticmethod
    def get_metadata(workspace_id: str) -> dict:
        ws_path = resolve_workspace_path(workspace_id)
        metadata = detect_repository_metadata(ws_path)
        metadata["workspace_id"] = workspace_id
        return metadata


    @staticmethod
    def package_fixed_repo(workspace_id: str) -> bytes:
        ws_path = resolve_workspace_path(workspace_id)
        return create_repository_zip(ws_path)
