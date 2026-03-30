from enum import StrEnum

from sqlalchemy import Column, Integer, String, Sequence, Text, DateTime

from backend.database import Base, db_session


class MessagesModel(Base):
    __tablename__ = 'messages'


    id = Column(Integer, Sequence("messages_id_seq"), primary_key=True, autoincrement=True)
    chat_session_id = Column(Integer, nullable=False)
    sender = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, server_default="CURRENT_TIMESTAMP", nullable=False)
    ref = Column(Text)
    tools_used = Column(Text)


class MessageSenderEnum(StrEnum):
    SYSTEM = "system"
    USER = "user"


def create_message(content: str, chat_session_id: int, references: list[str], tools_used: list[str], sender) -> MessagesModel:
    with db_session() as session:
        _new_message = MessagesModel(sender=sender.value, chat_session_id=chat_session_id, content=content,
                                     ref=",".join(references), tools_used=",".join(tools_used))

        session.add(_new_message)
        session.commit()
        session.refresh(_new_message)
        return _new_message


def get_messages_by_chat_id(chat_session_id: int) -> list[MessagesModel]:
    with db_session() as session:
        return session.query(
            MessagesModel.sender, MessagesModel.content, MessagesModel.ref, MessagesModel.tools_used
        ).filter(MessagesModel.chat_session_id == chat_session_id).all()
