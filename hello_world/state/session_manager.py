"""Session and conversation state management."""

import os
import json
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4
import uuid
import structlog


logger = structlog.get_logger()


class Session:
    """Represents a conversation session."""

    def __init__(
        self, session_id: str, conversation_id: str, project_path: Optional[str] = None
    ):
        self.id = session_id
        self.conversation_id = conversation_id
        self.project_path = project_path
        self.created_at = datetime.now().isoformat()
        self.messages: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}

    def add_user_message(self, text: str) -> None:
        """Add a user message to the session."""
        self.messages.append(
            {"role": "user", "content": text, "timestamp": datetime.now().isoformat()}
        )

    def add_ai_message(self, text: str) -> None:
        """Add an AI message to the session."""
        self.messages.append(
            {
                "role": "assistant",
                "content": text,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization."""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "project_path": self.project_path,
            "created_at": self.created_at,
            "messages": self.messages,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create session from dictionary."""
        session = cls(
            session_id=data["id"],
            conversation_id=data["conversation_id"],
            project_path=data.get("project_path"),
        )
        session.created_at = data["created_at"]
        session.messages = data["messages"]
        session.metadata = data.get("metadata", {})
        return session


class SessionManager:
    """Manages conversation sessions and persistence."""

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(
            base_path or "~/.conversation-system/projects"
        ).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_project_hash(self, project_path: str) -> str:
        """Generate hash for project path."""
        return hashlib.sha256(project_path.encode()).hexdigest()[:16]

    def _get_project_dir(self, project_path: str) -> Path:
        """Get project directory path."""
        project_hash = self._get_project_hash(project_path)
        return self.base_path / project_hash

    def _generate_uuid7(self) -> str:
        """Generate UUID for time-sortable IDs. Falls back to uuid4 if uuid7 not available."""
        try:
            return str(uuid.uuid7())  # type: ignore[attr-defined]
        except AttributeError:
            # uuid7 not available in older Python versions, use uuid4
            return str(uuid4())

    def _atomic_write(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Atomically write data to file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temporary file first
        with tempfile.NamedTemporaryFile(
            mode="w", dir=file_path.parent, delete=False, suffix=".tmp"
        ) as tmp_file:
            json.dump(data, tmp_file, indent=2, ensure_ascii=False)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
            tmp_path = tmp_file.name

        # Atomic move
        os.rename(tmp_path, file_path)

    def create_session(self, project_path: Optional[str] = None) -> Session:
        """Create a new session."""
        session_id = f"session_{self._generate_uuid7()}"
        conversation_id = f"conv_{self._generate_uuid7()}"

        # If project path provided, ensure directory structure exists
        if project_path:
            project_dir = self._get_project_dir(project_path)
            project_dir.mkdir(parents=True, exist_ok=True)

            # Save project metadata
            metadata_path = project_dir / "metadata.json"
            if not metadata_path.exists():
                metadata = {
                    "project_path": project_path,
                    "created_at": datetime.now().isoformat(),
                    "name": Path(project_path).name,
                }
                self._atomic_write(metadata_path, metadata)

            # Create conversation directory
            conv_dir = project_dir / "conversations" / conversation_id
            conv_dir.mkdir(parents=True, exist_ok=True)

            # Save conversation metadata
            conv_metadata_path = conv_dir / "metadata.json"
            conv_metadata = {
                "id": conversation_id,
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat(),
            }
            self._atomic_write(conv_metadata_path, conv_metadata)

        session = Session(session_id, conversation_id, project_path)
        logger.info(
            "Created new session",
            session_id=session_id,
            conversation_id=conversation_id,
            project_path=project_path,
        )

        return session

    def save_session(self, session: Session) -> None:
        """Save session to disk."""
        if not session.project_path:
            logger.warning(
                "No project path for session, not saving", session_id=session.id
            )
            return

        try:
            # Get session file path
            project_dir = self._get_project_dir(session.project_path)
            session_dir = (
                project_dir / "conversations" / session.conversation_id / "sessions"
            )
            session_file = session_dir / f"{session.id}.json"

            # Save session atomically
            self._atomic_write(session_file, session.to_dict())

            # Update conversation last accessed time
            conv_metadata_path = (
                project_dir
                / "conversations"
                / session.conversation_id
                / "metadata.json"
            )
            if conv_metadata_path.exists():
                with open(conv_metadata_path, "r") as f:
                    conv_metadata = json.load(f)

                conv_metadata["last_accessed"] = datetime.now().isoformat()
                self._atomic_write(conv_metadata_path, conv_metadata)

            logger.info(
                "Session saved",
                session_id=session.id,
                message_count=len(session.messages),
            )

        except Exception as e:
            logger.error("Failed to save session", session_id=session.id, error=str(e))
            raise

    def load_session(self, session_id: str, project_path: str) -> Optional[Session]:
        """Load a session from disk."""
        try:
            project_dir = self._get_project_dir(project_path)

            # Search for session in all conversations
            conversations_dir = project_dir / "conversations"
            if not conversations_dir.exists():
                return None

            for conv_dir in conversations_dir.iterdir():
                if not conv_dir.is_dir():
                    continue

                session_file = conv_dir / "sessions" / f"{session_id}.json"
                if session_file.exists():
                    try:
                        with open(session_file, "r") as f:
                            data = json.load(f)
                            return Session.from_dict(data)
                    except Exception as e:
                        logger.error(
                            "Failed to load session",
                            session_id=session_id,
                            conv_dir=conv_dir.name,
                            error=str(e),
                        )
                        continue

            return None

        except Exception as e:
            logger.error(
                "Failed to search for session",
                session_id=session_id,
                project_path=project_path,
                error=str(e),
            )
            return None

    def list_conversations(self, project_path: str) -> List[Dict[str, Any]]:
        """List all conversations for a project."""
        try:
            project_dir = self._get_project_dir(project_path)
            conversations_dir = project_dir / "conversations"

            if not conversations_dir.exists():
                return []

            conversations = []
            for conv_dir in conversations_dir.iterdir():
                if not conv_dir.is_dir():
                    continue

                metadata_file = conv_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, "r") as f:
                            metadata = json.load(f)

                        # Count sessions
                        sessions_dir = conv_dir / "sessions"
                        session_count = (
                            len(list(sessions_dir.glob("*.json")))
                            if sessions_dir.exists()
                            else 0
                        )

                        metadata["session_count"] = session_count
                        conversations.append(metadata)

                    except Exception as e:
                        logger.error(
                            "Failed to load conversation metadata",
                            conv_id=conv_dir.name,
                            error=str(e),
                        )

            # Sort by last accessed
            conversations.sort(key=lambda x: x.get("last_accessed", ""), reverse=True)
            return conversations

        except Exception as e:
            logger.error(
                "Failed to list conversations", project_path=project_path, error=str(e)
            )
            return []
