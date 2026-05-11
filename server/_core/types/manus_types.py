"""Manus OAuth API types"""
from typing import Optional
from pydantic import BaseModel


class AuthorizeRequest(BaseModel):
    redirectUri: str
    projectId: str
    state: str
    responseType: str
    scope: str


class AuthorizeResponse(BaseModel):
    redirectUrl: str


class ExchangeTokenRequest(BaseModel):
    grantType: str
    code: str
    refreshToken: Optional[str] = None
    clientId: str
    clientSecret: Optional[str] = None
    redirectUri: str


class ExchangeTokenResponse(BaseModel):
    accessToken: str
    tokenType: str
    expiresIn: int
    refreshToken: Optional[str] = None
    scope: str
    idToken: str


class GetUserInfoRequest(BaseModel):
    accessToken: str


class GetUserInfoResponse(BaseModel):
    openId: str
    projectId: str
    name: str
    email: Optional[str] = None
    platform: Optional[str] = None
    loginMethod: Optional[str] = None


class CanAccessRequest(BaseModel):
    openId: str
    projectId: str


class CanAccessResponse(BaseModel):
    canAccess: bool


class GetUserInfoWithJwtRequest(BaseModel):
    jwtToken: str
    projectId: str


class GetUserInfoWithJwtResponse(BaseModel):
    openId: str
    projectId: str
    name: str
    email: Optional[str] = None
    platform: Optional[str] = None
    loginMethod: Optional[str] = None

