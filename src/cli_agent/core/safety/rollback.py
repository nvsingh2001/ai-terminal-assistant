import hashlib
import os
import shutil
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FileSnapshot:
    file_path: str
    backup_path: str
    original_exists: bool
    timestamp: float = field(default_factory=time.time)


@dataclass
class EditTransaction:
    transaction_id: str
    snapshots: List[FileSnapshot] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class RollbackManager:
    """
    Manages atomic file snapshots and provides instant multi-file rollback (/undo) capabilities.
    Snapshots are stored in ~/.cli-agent/snapshots/<session_id>/.
    """

    def __init__(self, base_snapshot_dir: Optional[str] = None):
        if base_snapshot_dir is None:
            self.base_dir = os.path.expanduser("~/.cli-agent/snapshots")
        else:
            self.base_dir = base_snapshot_dir

        self.session_id = f"session_{int(time.time())}"
        self.session_dir = os.path.join(self.base_dir, self.session_id)
        os.makedirs(self.session_dir, exist_ok=True)

        self.transaction_stack: List[EditTransaction] = []
        self._current_transaction: Optional[EditTransaction] = None

    def begin_transaction(self, transaction_id: Optional[str] = None) -> EditTransaction:
        """Starts a new atomic edit transaction."""
        t_id = transaction_id or f"tx_{int(time.time() * 1000)}"
        self._current_transaction = EditTransaction(transaction_id=t_id)
        return self._current_transaction

    def record_pre_edit(self, file_path: str) -> Optional[FileSnapshot]:
        """
        Creates a shadow backup of the file before any modification occurs.
        If no active transaction is open, automatically creates and commits one.
        """
        abs_path = os.path.abspath(file_path)
        auto_commit = False

        if self._current_transaction is None:
            self.begin_transaction()
            auto_commit = True

        # Check if already snapshotted in current transaction
        for snap in self._current_transaction.snapshots:
            if snap.file_path == abs_path:
                return snap

        file_exists = os.path.exists(abs_path)
        path_hash = hashlib.sha256(abs_path.encode()).hexdigest()[:12]
        backup_filename = f"{path_hash}_{os.path.basename(abs_path)}.bak"
        backup_path = os.path.join(self.session_dir, backup_filename)

        if file_exists:
            try:
                shutil.copy2(abs_path, backup_path)
            except Exception:
                pass
        else:
            backup_path = ""

        snapshot = FileSnapshot(
            file_path=abs_path,
            backup_path=backup_path,
            original_exists=file_exists,
        )
        self._current_transaction.snapshots.append(snapshot)

        if auto_commit:
            self.commit_transaction()

        return snapshot

    def commit_transaction(self):
        """Finalizes the active transaction and pushes it onto the rollback stack."""
        if self._current_transaction and self._current_transaction.snapshots:
            self.transaction_stack.append(self._current_transaction)
        self._current_transaction = None

    def rollback_last_transaction(self) -> List[str]:
        """
        Reverts the most recent transaction, restoring all affected files to their exact pre-edit state.
        Returns the list of restored file paths.
        """
        if not self.transaction_stack:
            return []

        transaction = self.transaction_stack.pop()
        restored_files: List[str] = []

        for snapshot in reversed(transaction.snapshots):
            target_path = snapshot.file_path
            try:
                if snapshot.original_exists and snapshot.backup_path and os.path.exists(snapshot.backup_path):
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    shutil.copy2(snapshot.backup_path, target_path)
                    restored_files.append(target_path)
                elif not snapshot.original_exists and os.path.exists(target_path):
                    # File was newly created by the agent, remove it
                    os.remove(target_path)
                    restored_files.append(f"{target_path} (removed newly created file)")
            except Exception as e:
                print(f"Warning: Failed to rollback file {target_path}: {e}")

        return restored_files

    def clear(self):
        """Cleans up the transaction stack and snapshot directory."""
        self.transaction_stack.clear()
        self._current_transaction = None
        try:
            if os.path.exists(self.session_dir):
                shutil.rmtree(self.session_dir)
        except Exception:
            pass


# Global singleton instance
rollback_manager = RollbackManager()
