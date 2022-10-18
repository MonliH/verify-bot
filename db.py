from typing import Optional, Union
import motor.motor_asyncio
from dataclasses import dataclass
from os import environ

client = motor.motor_asyncio.AsyncIOMotorClient(environ["DB_CONNECTION"])

db = client.verify
state_collection = db["state"]
used_emails = db["used"]


@dataclass
class SentVerification:
    email: str
    code: str


@dataclass
class Verified:
    pass


Status = Union[SentVerification, Verified]


async def set_state(snowflake: int, status: Status):
    match status:
        case SentVerification(email, code):
            await state_collection.insert_one(
                {
                    "snowflake": snowflake,
                    "status": {"type": "sent", "email": email, "code": code},
                }
            )
        case Verified:
            await state_collection.update_one(
                {"snowflake": snowflake}, {"$set": {"status": {"type": "verified"}}}
            )


async def reset_state(snowflake: int):
    await state_collection.delete_one({"snowflake": snowflake})


async def get_state(snowflake: int) -> Optional[Status]:
    v = await state_collection.find_one({"snowflake": snowflake})
    if not v:
        return None
    v = v["status"]
    if v["type"] == "sent":
        return SentVerification(v["email"], v["code"])
    elif v["type"] == "verified":
        return Verified()


async def add_email(email: str, userid: str):
    await used_emails.insert_one({"email": email, "userid": userid})


async def used_email(email: str) -> bool:
    return bool(await used_emails.find_one({"email": email}))
