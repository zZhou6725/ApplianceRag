from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str | None = Field(default=None, description="对话 ID，为空则创建新对话")
    message: str = Field(..., min_length=1, description="用户消息")
    file_context: str | None = Field(default=None, description="上传文件的文本内容（可选）")
    file_name: str | None = Field(default=None, description="上传文件的文件名（可选）")


class MessageData(BaseModel):
    message_id: str = Field(..., description="消息唯一 ID")
    conversation_id: str = Field(..., description="所属对话 ID")
    role: str = Field(..., description="user 或 assistant")
    content: str = Field(..., description="消息内容")
    created_at: datetime | None = Field(default=None, description="创建时间")


class ConversationResponse(BaseModel):
    conversation_id: str = Field(..., description="对话 ID")
    title: str = Field(..., description="对话标题")
    messages: list[MessageData] = Field(default_factory=list, description="消息列表")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")


class ConversationListItem(BaseModel):
    conversation_id: str = Field(..., description="对话 ID")
    title: str = Field(..., description="对话标题")
    message_count: int = Field(default=0, description="消息数量")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")


class ConversationListResponse(BaseModel):
    total: int = Field(..., ge=0, description="总数")
    items: list[ConversationListItem] = Field(default_factory=list, description="对话列表")
