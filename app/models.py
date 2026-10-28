from dataclasses import dataclass
from datetime import datetime
from typing import Optional

class MessageStatus:
    NEW = "new"
    SENT = "sent"
    OPENED = "opened"
    SKIPPED = "skipped"
    SPAM = "spam"

@dataclass
class Source:
    tg_id: int
    username: Optional[str] = None
    title: Optional[str] = None
    paused: bool = False

@dataclass
class Message:
    source_tg_id: int
    tg_message_id: int
    text: str
    links: str
    features: str
    score: int
    hash: str
    status: str = MessageStatus.NEW
    id: Optional[int] = None
    created_at: Optional[datetime] = None

@dataclass
class Feedback:
    message_id: int
    action: str
    id: Optional[int] = None
    created_at: Optional[datetime] = None