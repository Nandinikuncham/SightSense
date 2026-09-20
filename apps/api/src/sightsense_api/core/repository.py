"""Repository abstractions and adapters for SightSense data storage.

Includes abstract interfaces and two concrete implementations:
1. InMemoryRepository: Fast, deterministic, zero-dependency in-memory store for local testing.
2. DynamoDBRepository: Single-table production DynamoDB repository using boto3.
"""

from abc import ABC, abstractmethod
from typing import Any

import boto3
from botocore.exceptions import ClientError

from sightsense_api.core.errors import UpstreamServiceError
from sightsense_api.core.logging import get_logger
from sightsense_api.core.models import (
    Analysis,
    Feedback,
    Session,
    Upload,
    User,
)

logger = get_logger("sightsense_api.repository")


class RepositoryInterface(ABC):
    """Abstract data access layer for domain entities."""

    # Users
    @abstractmethod
    async def create_user(self, user: User) -> User: ...

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> User | None: ...

    @abstractmethod
    async def get_user_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool: ...

    # Sessions
    @abstractmethod
    async def create_session(self, session: Session) -> Session: ...

    @abstractmethod
    async def get_session(self, session_id: str) -> Session | None: ...

    @abstractmethod
    async def update_session(self, session: Session) -> Session: ...

    @abstractmethod
    async def list_sessions_by_user(
        self, user_id: str, limit: int = 20, cursor: str | None = None
    ) -> tuple[list[Session], str | None]: ...

    # Uploads
    @abstractmethod
    async def create_upload(self, upload: Upload) -> Upload: ...

    @abstractmethod
    async def get_upload(self, upload_id: str) -> Upload | None: ...

    @abstractmethod
    async def update_upload(self, upload: Upload) -> Upload: ...

    # Analyses
    @abstractmethod
    async def create_analysis(self, analysis: Analysis) -> Analysis: ...

    @abstractmethod
    async def get_analysis(self, analysis_id: str) -> Analysis | None: ...

    @abstractmethod
    async def update_analysis(self, analysis: Analysis) -> Analysis: ...

    @abstractmethod
    async def list_analyses_by_session(
        self, session_id: str, limit: int = 20
    ) -> list[Analysis]: ...

    # Feedback
    @abstractmethod
    async def create_feedback(self, feedback: Feedback) -> Feedback: ...

    @abstractmethod
    async def list_feedback_by_user(self, user_id: str, limit: int = 50) -> list[Feedback]: ...


class InMemoryRepository(RepositoryInterface):
    """In-memory thread-safe dictionary store for development and testing."""

    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.users_by_email: dict[str, str] = {}
        self.sessions: dict[str, Session] = {}
        self.uploads: dict[str, Upload] = {}
        self.analyses: dict[str, Analysis] = {}
        self.feedbacks: dict[str, Feedback] = {}

    # Users
    async def create_user(self, user: User) -> User:
        self.users[user.user_id] = user
        self.users_by_email[user.email.lower()] = user.user_id
        return user

    async def get_user_by_id(self, user_id: str) -> User | None:
        return self.users.get(user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        uid = self.users_by_email.get(email.lower())
        if not uid:
            return None
        return self.users.get(uid)

    async def delete_user(self, user_id: str) -> bool:
        user = self.users.pop(user_id, None)
        if user:
            self.users_by_email.pop(user.email.lower(), None)
            return True
        return False

    # Sessions
    async def create_session(self, session: Session) -> Session:
        self.sessions[session.session_id] = session
        return session

    async def get_session(self, session_id: str) -> Session | None:
        return self.sessions.get(session_id)

    async def update_session(self, session: Session) -> Session:
        self.sessions[session.session_id] = session
        return session

    async def list_sessions_by_user(
        self, user_id: str, limit: int = 20, cursor: str | None = None
    ) -> tuple[list[Session], str | None]:
        user_sessions = [
            s for s in self.sessions.values() if s.user_id == user_id
        ]
        user_sessions.sort(key=lambda s: s.started_at, reverse=True)

        start_idx = 0
        if cursor:
            try:
                start_idx = int(cursor)
            except ValueError:
                start_idx = 0

        page = user_sessions[start_idx : start_idx + limit]
        next_cursor = str(start_idx + limit) if start_idx + limit < len(user_sessions) else None
        return page, next_cursor

    # Uploads
    async def create_upload(self, upload: Upload) -> Upload:
        self.uploads[upload.upload_id] = upload
        return upload

    async def get_upload(self, upload_id: str) -> Upload | None:
        return self.uploads.get(upload_id)

    async def update_upload(self, upload: Upload) -> Upload:
        self.uploads[upload.upload_id] = upload
        return upload

    # Analyses
    async def create_analysis(self, analysis: Analysis) -> Analysis:
        self.analyses[analysis.analysis_id] = analysis
        return analysis

    async def get_analysis(self, analysis_id: str) -> Analysis | None:
        return self.analyses.get(analysis_id)

    async def update_analysis(self, analysis: Analysis) -> Analysis:
        self.analyses[analysis.analysis_id] = analysis
        return analysis

    async def list_analyses_by_session(
        self, session_id: str, limit: int = 20
    ) -> list[Analysis]:
        session_analyses = [
            a for a in self.analyses.values() if a.session_id == session_id
        ]
        session_analyses.sort(key=lambda a: a.created_at, reverse=True)
        return session_analyses[:limit]

    # Feedback
    async def create_feedback(self, feedback: Feedback) -> Feedback:
        self.feedbacks[feedback.feedback_id] = feedback
        return feedback

    async def list_feedback_by_user(self, user_id: str, limit: int = 50) -> list[Feedback]:
        user_feedback = [f for f in self.feedbacks.values() if f.user_id == user_id]
        user_feedback.sort(key=lambda f: f.created_at, reverse=True)
        return user_feedback[:limit]


class DynamoDBRepository(RepositoryInterface):
    """Production DynamoDB Single-Table Repository."""

    def __init__(self, table_name: str, region_name: str = "ap-south-1") -> None:
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb", region_name=region_name)
        self.table = self.dynamodb.Table(table_name)

    # Users
    async def create_user(self, user: User) -> User:
        item = {
            "PK": f"USER#{user.user_id}",
            "SK": "METADATA",
            "GSI1PK": f"EMAIL#{user.email.lower()}",
            "GSI1SK": "METADATA",
            "entity_type": "User",
            **user.model_dump(mode="json"),
        }
        try:
            self.table.put_item(Item=item)
            return user
        except ClientError as e:
            logger.error(f"DynamoDB error putting user: {e}")
            raise UpstreamServiceError(message="Database operation failed")

    async def get_user_by_id(self, user_id: str) -> User | None:
        try:
            res = self.table.get_item(Key={"PK": f"USER#{user_id}", "SK": "METADATA"})
            item = res.get("Item")
            if not item:
                return None
            return User.model_validate(item)
        except ClientError as e:
            logger.error(f"DynamoDB error getting user: {e}")
            raise UpstreamServiceError(message="Database operation failed")

    async def get_user_by_email(self, email: str) -> User | None:
        try:
            res = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1PK = :email AND GSI1SK = :meta",
                ExpressionAttributeValues={
                    ":email": f"EMAIL#{email.lower()}",
                    ":meta": "METADATA",
                },
            )
            items = res.get("Items", [])
            if not items:
                return None
            return User.model_validate(items[0])
        except ClientError as e:
            logger.error(f"DynamoDB error querying user by email: {e}")
            raise UpstreamServiceError(message="Database operation failed")

    async def delete_user(self, user_id: str) -> bool:
        try:
            self.table.delete_item(Key={"PK": f"USER#{user_id}", "SK": "METADATA"})
            return True
        except ClientError as e:
            logger.error(f"DynamoDB error deleting user: {e}")
            raise UpstreamServiceError(message="Database operation failed")

    # Sessions
    async def create_session(self, session: Session) -> Session:
        item = {
            "PK": f"USER#{session.user_id}",
            "SK": f"SESSION#{session.session_id}",
            "GSI1PK": f"SESSION#{session.session_id}",
            "GSI1SK": "METADATA",
            "entity_type": "Session",
            **session.model_dump(mode="json"),
        }
        try:
            self.table.put_item(Item=item)
            return session
        except ClientError as e:
            logger.error(f"DynamoDB error putting session: {e}")
            raise UpstreamServiceError(message="Database operation failed")

    async def get_session(self, session_id: str) -> Session | None:
        try:
            res = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1PK = :sid AND GSI1SK = :meta",
                ExpressionAttributeValues={":sid": f"SESSION#{session_id}", ":meta": "METADATA"},
            )
            items = res.get("Items", [])
            if not items:
                return None
            return Session.model_validate(items[0])
        except ClientError as e:
            logger.error(f"DynamoDB error getting session: {e}")
            raise UpstreamServiceError(message="Database operation failed")

    async def update_session(self, session: Session) -> Session:
        return await self.create_session(session)

    async def list_sessions_by_user(
        self, user_id: str, limit: int = 20, cursor: str | None = None
    ) -> tuple[list[Session], str | None]:
        params: dict[str, Any] = {
            "KeyConditionExpression": "PK = :uid AND begins_with(SK, :ses_prefix)",
            "ExpressionAttributeValues": {
                ":uid": f"USER#{user_id}",
                ":ses_prefix": "SESSION#",
            },
            "Limit": limit,
            "ScanIndexForward": False,
        }
        if cursor:
            params["ExclusiveStartKey"] = {"PK": f"USER#{user_id}", "SK": cursor}

        try:
            res = self.table.query(**params)
            sessions = [Session.model_validate(item) for item in res.get("Items", [])]
            last_key = res.get("LastEvaluatedKey")
            next_cursor = last_key.get("SK") if last_key else None
            return sessions, next_cursor
        except ClientError as e:
            logger.error(f"DynamoDB error listing sessions: {e}")
            raise UpstreamServiceError(message="Database operation failed")

    # Uploads
    async def create_upload(self, upload: Upload) -> Upload:
        ttl = int(upload.expires_at.timestamp())
        item = {
            "PK": f"UPLOAD#{upload.upload_id}",
            "SK": "METADATA",
            "entity_type": "Upload",
            "TTL": ttl,
            **upload.model_dump(mode="json"),
        }
        try:
            self.table.put_item(Item=item)
            return upload
        except ClientError as e:
            logger.error(f"DynamoDB error creating upload: {e}")
            raise UpstreamServiceError(message="Database operation failed")

    async def get_upload(self, upload_id: str) -> Upload | None:
        try:
            res = self.table.get_item(Key={"PK": f"UPLOAD#{upload_id}", "SK": "METADATA"})
            item = res.get("Item")
            if not item:
                return None
            return Upload.model_validate(item)
        except ClientError as e:
            logger.error(f"DynamoDB error getting upload: {e}")
            raise UpstreamServiceError(message="Database operation failed")

    async def update_upload(self, upload: Upload) -> Upload:
        return await self.create_upload(upload)

    # Analyses
    async def create_analysis(self, analysis: Analysis) -> Analysis:
        item = {
            "PK": f"SESSION#{analysis.session_id}",
            "SK": f"ANALYSIS#{analysis.analysis_id}",
            "GSI1PK": f"ANALYSIS#{analysis.analysis_id}",
            "GSI1SK": "METADATA",
            "entity_type": "Analysis",
            **analysis.model_dump(mode="json"),
        }
        try:
            self.table.put_item(Item=item)
            return analysis
        except ClientError as e:
            logger.error(f"DynamoDB error creating analysis: {e}")
            raise UpstreamServiceError(message="Database operation failed")

    async def get_analysis(self, analysis_id: str) -> Analysis | None:
        try:
            res = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1PK = :aid AND GSI1SK = :meta",
                ExpressionAttributeValues={":aid": f"ANALYSIS#{analysis_id}", ":meta": "METADATA"},
            )
            items = res.get("Items", [])
            if not items:
                return None
            return Analysis.model_validate(items[0])
        except ClientError as e:
            logger.error(f"DynamoDB error getting analysis: {e}")
            raise UpstreamServiceError(message="Database operation failed")

    async def update_analysis(self, analysis: Analysis) -> Analysis:
        return await self.create_analysis(analysis)

    async def list_analyses_by_session(
        self, session_id: str, limit: int = 20
    ) -> list[Analysis]:
        try:
            res = self.table.query(
                KeyConditionExpression="PK = :sid AND begins_with(SK, :ana_prefix)",
                ExpressionAttributeValues={
                    ":sid": f"SESSION#{session_id}",
                    ":ana_prefix": "ANALYSIS#",
                },
                Limit=limit,
                ScanIndexForward=False,
            )
            return [Analysis.model_validate(item) for item in res.get("Items", [])]
        except ClientError as e:
            logger.error(f"DynamoDB error listing analyses: {e}")
            raise UpstreamServiceError(message="Database operation failed")

    # Feedback
    async def create_feedback(self, feedback: Feedback) -> Feedback:
        item = {
            "PK": f"USER#{feedback.user_id}",
            "SK": f"FEEDBACK#{feedback.feedback_id}",
            "entity_type": "Feedback",
            **feedback.model_dump(mode="json"),
        }
        try:
            self.table.put_item(Item=item)
            return feedback
        except ClientError as e:
            logger.error(f"DynamoDB error creating feedback: {e}")
            raise UpstreamServiceError(message="Database operation failed")

    async def list_feedback_by_user(self, user_id: str, limit: int = 50) -> list[Feedback]:
        try:
            res = self.table.query(
                KeyConditionExpression="PK = :uid AND begins_with(SK, :fdb_prefix)",
                ExpressionAttributeValues={
                    ":uid": f"USER#{user_id}",
                    ":fdb_prefix": "FEEDBACK#",
                },
                Limit=limit,
                ScanIndexForward=False,
            )
            return [Feedback.model_validate(item) for item in res.get("Items", [])]
        except ClientError as e:
            logger.error(f"DynamoDB error listing feedback: {e}")
            raise UpstreamServiceError(message="Database operation failed")
