from sqlalchemy import Column, Integer, Sequence, DateTime, String, func

from backend.database import Base, db_session


class ChatSessionModel(Base):
    __tablename__ = 'chat_session'


    id = Column(Integer, Sequence("chat_session_id_seq"), primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, server_default="CURRENT_TIMESTAMP", nullable=False)
    last_message_time = Column(DateTime, server_default="CURRENT_TIMESTAMP", nullable=False)


def create_chat_session(user_id: int) -> ChatSessionModel:
    with db_session() as session:
        _chat_session = ChatSessionModel(user_id=user_id, title='Untitled')
        session.add(_chat_session)
        session.commit()

        session.refresh(_chat_session)
        return _chat_session


def fetch_chat_session_by_id(chat_session_id: int) -> ChatSessionModel:
    with db_session() as session:
        return session.query(ChatSessionModel).filter(ChatSessionModel.id == chat_session_id).first()

def fetch_chat_sessions_by_user_id(user_id: int) -> list:
    with db_session() as session:
        return session.query(ChatSessionModel.id, ChatSessionModel.title).filter(ChatSessionModel.user_id == user_id).all()


def update_last_message_time(chat_session_id: int) -> ChatSessionModel:
    chat_session = fetch_chat_session_by_id(chat_session_id)

    with db_session() as session:
        chat_session.last_message_time = func.now()

        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)
        return chat_session


def update_chat_session_title(chat_session_id: int, title: str) -> ChatSessionModel:
    chat_session = fetch_chat_session_by_id(chat_session_id)

    with db_session() as session:
        chat_session.title = title
        chat_session.last_message_time = func.now()

        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)
        return chat_session
