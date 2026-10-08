import os
import json
import math
import asyncio
import threading
from datetime import datetime, timezone

import aiohttp
from flask import Flask

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ChatType
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
)


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = "8701693363:AAG0disLU7BfVm1hmD9xAPpaYzmVYDs9GZI"

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable is missing."
    )

ADMIN_ID = 8333711029

API_URL = "https://akash-number-lookup.vercel.app/api/search"
API_KEY = "DEMO"

RECORDS_PER_PAGE = 3

USERS_FILE = "users.json"
VERIFIED_FILE = "verified.json"
QUERIES_FILE = "queries.json"
APPROVED_GROUPS_FILE = "approved_groups.json"


# ============================================================
# FLASK HEALTH SERVER FOR RENDER
# ============================================================

health_app = Flask(__name__)


@health_app.route("/")
def home():
    return "AKASH NUMBER LOOKUP BOT ONLINE", 200


@health_app.route("/health")
def health():
    return "OK", 200


def run_health_server():
    port = int(os.getenv("PORT", "10000"))

    health_app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False,
    )


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(filename, default):
    try:
        if not os.path.exists(filename):
            return default

        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception as error:
        print(f"JSON LOAD ERROR [{filename}]:", repr(error))
        return default


def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
            )
        return True

    except Exception as error:
        print(f"JSON SAVE ERROR [{filename}]:", repr(error))
        return False


# ============================================================
# USER DATA
# ============================================================

def get_users():
    return load_json(USERS_FILE, {})


def save_users(data):
    save_json(USERS_FILE, data)


def get_verified():
    return load_json(VERIFIED_FILE, {})


def save_verified(data):
    save_json(VERIFIED_FILE, data)


def get_queries():
    return load_json(QUERIES_FILE, [])


def save_queries(data):
    save_json(QUERIES_FILE, data)


def get_approved_groups():
    return load_json(APPROVED_GROUPS_FILE, [])


def save_approved_groups(data):
    save_json(APPROVED_GROUPS_FILE, data)


# ============================================================
# USER REGISTRATION
# ============================================================

def register_user(user):
    users = get_users()

    user_id = str(user.id)

    users[user_id] = {
        "user_id": user.id,
        "name": user.full_name,
        "username": user.username,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    save_users(users)


def is_verified(user_id):
    verified = get_verified()
    return str(user_id) in verified


# ============================================================
# MAIN KEYBOARD
# ============================================================

def main_keyboard(user_id):
    rows = [
        [
            KeyboardButton("🔎 Number Lookup"),
            KeyboardButton("👤 My Contact"),
        ],
        [
            KeyboardButton("❓ Help"),
        ],
    ]

    if user_id == ADMIN_ID:
        rows.append(
            [
                KeyboardButton("⚙️ Bot Management"),
            ]
        )

    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        is_persistent=True,
    )


# ============================================================
# CONTACT VERIFICATION KEYBOARD
# ============================================================

def contact_keyboard():
    keyboard = [
        [
            KeyboardButton(
                "📱 Share My Contact",
                request_contact=True,
            )
        ]
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user:
        return

    register_user(user)

    if not is_verified(user.id):

        await update.message.reply_text(
            "🔐 Verification required.\n\n"
            "Please share your own Telegram contact "
            "using the button below.",
            reply_markup=contact_keyboard(),
        )

        return

    await update.message.reply_text(
        "👋 Welcome to Number Lookup Bot.\n\n"
        "Choose an option from the menu below.",
        reply_markup=main_keyboard(user.id),
    )


# ============================================================
# CONTACT VERIFICATION
# ============================================================

async def handle_contact(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.message

    if not user or not message or not message.contact:
        return

    contact = message.contact

    # Only allow user's own Telegram contact
    if contact.user_id != user.id:

        await message.reply_text(
            "❌ Please share your own Telegram contact.\n\n"
            "The contact must belong to your Telegram account.",
            reply_markup=contact_keyboard(),
        )

        return

    verified = get_verified()

    verified[str(user.id)] = {
        "user_id": user.id,
        "name": user.full_name,
        "username": user.username,
        "contact": contact.phone_number,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }

    save_verified(verified)

    await message.reply_text(
        "✅ Verification successful!\n\n"
        "You can now use Number Lookup.",
        reply_markup=main_keyboard(user.id),
    )


# ============================================================
# HELP
# ============================================================

async def show_help(update: Update):
    await update.message.reply_text(
        "𝑵𝒆𝒆𝒅 𝒂𝒔𝒔𝒊𝒔𝒕𝒂𝒏𝒄𝒆?\n\n"
        "𝑭𝒐𝒓 𝒔𝒖𝒑𝒑𝒐𝒓𝒕, 𝒊𝒔𝒔𝒖𝒆𝒔 𝒐𝒓 𝒈𝒆𝒏𝒆𝒓𝒂𝒍 "
        "𝒊𝒏𝒒𝒖𝒊𝒓𝒊𝒆𝒔, 𝒑𝒍𝒆𝒂𝒔𝒆 𝒄𝒐𝒏𝒕𝒂𝒄𝒕 𝒕𝒉𝒆 𝒂𝒅𝒎𝒊𝒏.\n\n"
        "👨‍💻 𝑨𝒅𝒎𝒊𝒏 ~ @AK4SX"
    )


# ============================================================
# MY CONTACT
# ============================================================

async def show_my_contact(update: Update):
    user = update.effective_user

    verified = get_verified()
    record = verified.get(str(user.id))

    if not record:
        await update.message.reply_text(
            "❌ You are not verified yet.",
            reply_markup=contact_keyboard(),
        )
        return

    contact = record.get("contact")

    await update.message.reply_text(
        "👤 𝗬𝗼𝘂𝗿 𝗖𝗼𝗻𝘁𝗮𝗰𝘁\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 𝗡𝗮𝗺𝗲      • {record.get('name') or 'N/A'}\n"
        f"🆔 𝗨𝘀𝗲𝗿 𝗜𝗗   • {record.get('user_id')}\n"
        f"🏷️ 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲  • @{record.get('username') or 'N/A'}\n"
        f"☎️ 𝗖𝗼𝗻𝘁𝗮𝗰𝘁   • {contact or 'N/A'}"
    )


# ============================================================
# NUMBER NORMALIZATION
# ============================================================

def clean_number(text):
    if not text:
        return ""

    number = text.strip()

    for char in [" ", "-", "(", ")", "."]:
        number = number.replace(char, "")

    if number.startswith("+91"):
        number = number[3:]

    if number.startswith("91") and len(number) == 12:
        number = number[2:]

    return number


# ============================================================
# API RECORD EXTRACTION
# ============================================================

def extract_records(data):

    if not isinstance(data, dict):
        return []

    possible_keys = [
        "data",
        "results",
        "records",
    ]

    for key in possible_keys:

        value = data.get(key)

        if isinstance(value, list):
            return value

        if isinstance(value, dict):
            return [value]

    # Single record fallback
    if any(
        key in data
        for key in [
            "name",
            "mobile",
            "phone",
            "phoneNumber",
        ]
    ):
        return [data]

    return []


# ============================================================
# SAFE RECORD FORMAT
# ============================================================

def make_safe_record(record):

    if not isinstance(record, dict):
        return {
            "aadhar": "N/A",
            "mobile": "N/A",
            "name": "N/A",
            "father": "N/A",
            "address": "N/A",
            "alt_mobile": "N/A",
            "circle": "N/A",
        }

    mobile = (
        record.get("mobile")
        or record.get("phone")
        or record.get("phoneNumber")
    )

    name = (
        record.get("name")
        or record.get("full_name")
        or record.get("fullName")
    )

    father = (
        record.get("father")
        or record.get("father_name")
        or record.get("fatherName")
    )

    address = record.get("address")

    alternate = (
        record.get("alt_mobile")
        or record.get("alternate")
        or record.get("alternate_mobile")
        or record.get("alternateMobile")
    )

    aadhar = (
        record.get("aadhar")
        or record.get("aadhaar")
        or record.get("aadhaar_number")
    )

    circle = (
        record.get("circle")
        or record.get("operator_circle")
        or record.get("region")
        or "N/A"
    )

    # &amp; ko & mein convert karo
    circle = str(circle).replace("&amp;", "&")

    return {
        # Aadhaar, Mobile, Alt Mobile full show honge
        "aadhar": str(aadhar) if aadhar else "N/A",
        "mobile": str(mobile) if mobile else "N/A",
        "name": str(name) if name else "N/A",
        "father": str(father) if father else "N/A",
        "address": str(address) if address else "N/A",
        "alt_mobile": str(alternate) if alternate else "N/A",
        "circle": circle,
    }


# ============================================================
# FORMAT ONE RECORD
# ============================================================

def format_single_record(record, index):

    return (
        f"╭──────── RECORD {index} ────────╮\n"
        f"│\n"
        f"│ 🪪 𝗔𝗮𝗱𝗵𝗮𝗿 • {record['aadhar']}\n"
        f"│ 📞 𝗠𝗼𝗯𝗶𝗹𝗲 • {record['mobile']}\n"
        f"│ 👤 𝗡𝗮𝗺𝗲 • {record['name']}\n"
        f"│ 👨‍👦 𝗙𝗮𝘁𝗵𝗲𝗿 • {record['father']}\n"
        f"│ 📍 𝗔𝗱𝗱𝗿𝗲𝘀𝘀 • {record['address']}\n"
        f"│ 📱 𝗔𝗹𝘁 𝗠𝗼𝗯𝗶𝗹𝗲 • {record['alt_mobile']}\n"
        f"│ 📡 𝗖𝗶𝗿𝗰𝗹𝗲 • {record['circle']}\n"
        f"│\n"
        f"╰──────────────────────────╯"
    )


# ============================================================
# BUILD PAGINATION PAGE
# ============================================================

def build_page(records, number, page):

    total = len(records)

    total_pages = max(
        1,
        math.ceil(total / RECORDS_PER_PAGE)
    )

    page = max(
        0,
        min(page, total_pages - 1)
    )

    start = page * RECORDS_PER_PAGE
    end = start + RECORDS_PER_PAGE

    page_records = records[start:end]

    lines = [
        "📋 𝗡𝗨𝗠𝗕𝗘𝗥 𝗟𝗢𝗢𝗞𝗨𝗣",
        "━━━━━━━━━━━━━━━━━━",
        f"📞 𝗡𝘂𝗺𝗯𝗲𝗿 • {number}",
        f"📊 𝗧𝗼𝘁𝗮𝗹 𝗥𝗲𝗰𝗼𝗿𝗱𝘀 • {total}",
        f"📄 𝗣𝗮𝗴𝗲 • {page + 1}/{total_pages}",
        "🔎 𝗦𝘁𝗮𝘁𝘂𝘀 • Success",
        "",
    ]

    for position, record in enumerate(
        page_records,
        start=start + 1,
    ):
        lines.append(
            format_single_record(
                record,
                position,
            )
        )

        lines.append("")

    lines.append(
        "├ 🛠️ ᴅᴇᴠᴇʟᴏᴘᴇʀ: ᴅᴇᴇᴘᴀᴋ • 🛰️"
    )

    return "\n".join(lines)


# ============================================================
# PAGINATION KEYBOARD
# ============================================================

def pagination_keyboard(number, page, total):

    total_pages = max(
        1,
        math.ceil(total / RECORDS_PER_PAGE)
    )

    buttons = []

    if page > 0:
        buttons.append(
            InlineKeyboardButton(
                "◀️ Previous",
                callback_data=f"lookup:{number}:{page - 1}",
            )
        )

    buttons.append(
        InlineKeyboardButton(
            f"📄 {page + 1}/{total_pages}",
            callback_data="lookup:page",
        )
    )

    if page < total_pages - 1:
        buttons.append(
            InlineKeyboardButton(
                "Next ▶️",
                callback_data=f"lookup:{number}:{page + 1}",
            )
        )

    return InlineKeyboardMarkup([buttons])


# ============================================================
# SAVE QUERY
# ============================================================

def save_query(user, number):

    queries = get_queries()

    queries.append(
        {
            "user_id": user.id,
            "name": user.full_name,
            "username": user.username,
            "number": number,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }
    )

    # Keep latest 25
    queries = queries[-25:]

    save_queries(queries)


# ============================================================
# NUMBER LOOKUP
# ============================================================

async def process_number(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    number: str,
):

    user = update.effective_user

    clean = clean_number(number)

    if not clean.isdigit() or len(clean) != 10:

        await update.message.reply_text(
            "❌ Please send a valid 10-digit mobile number.\n\n"
            "Example:\n"
            "9876543210"
        )

        return

    save_query(user, clean)

    searching_message = await update.message.reply_text(
        "🔎 Searching authorized/test records..."
    )

    try:

        timeout = aiohttp.ClientTimeout(
            total=30
        )

        params = {
            "key": API_KEY,
            "query": clean,
        }

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(
                API_URL,
                params=params,
            ) as response:

                raw = await response.text()

                print("=" * 50)
                print("API STATUS:", response.status)
                print("API URL:", str(response.url))
                print("API RESPONSE:", raw[:5000])
                print("=" * 50)

                if response.status != 200:

                    await searching_message.edit_text(
                        "❌ API Error\n\n"
                        f"HTTP Status: {response.status}\n\n"
                        f"{raw[:1000]}"
                    )

                    return

                try:
                    data = json.loads(raw)

                except json.JSONDecodeError:

                    await searching_message.edit_text(
                        "❌ API ne valid JSON response nahi diya.\n\n"
                        + raw[:1000]
                    )

                    return

    except asyncio.TimeoutError:

        await searching_message.edit_text(
            "⏱️ API request timeout.\n\n"
            "Please try again."
        )

        return

    except Exception as error:

        print(
            "API ERROR:",
            repr(error),
        )

        await searching_message.edit_text(
            "❌ API connection error.\n\n"
            "Please try again later."
        )

        return

    records = extract_records(data)

    safe_records = [
        make_safe_record(record)
        for record in records
    ]

    if not safe_records:

        await searching_message.edit_text(
            "📋 𝗡𝗨𝗠𝗕𝗘𝗥 𝗟𝗢𝗢𝗞𝗨𝗣\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"📞 𝗡𝘂𝗺𝗯𝗲𝗿 • {clean}\n"
            "📊 𝗧𝗼𝘁𝗮𝗹 𝗥𝗲𝗰𝗼𝗿𝗱𝘀 • 0\n"
            "🔎 𝗦𝘁𝗮𝘁𝘂𝘀 • No records found\n\n"
            "No authorized/test record was found."
        )

        return

    # Store records for pagination
    context.user_data["lookup_records"] = safe_records
    context.user_data["lookup_number"] = clean

    text = build_page(
        safe_records,
        clean,
        0,
    )

    keyboard = pagination_keyboard(
        clean,
        0,
        len(safe_records),
    )

    await searching_message.edit_text(
        text,
        reply_markup=keyboard,
    )


# ============================================================
# PAGINATION CALLBACK
# ============================================================

async def pagination_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    data = query.data

    if data == "lookup:page":
        return

    if not data.startswith("lookup:"):
        return

    parts = data.split(":")

    if len(parts) != 3:
        return

    number = parts[1]

    try:
        page = int(parts[2])

    except ValueError:
        return

    records = context.user_data.get(
        "lookup_records",
        [],
    )

    stored_number = context.user_data.get(
        "lookup_number"
    )

    if stored_number != number:
        await query.edit_message_text(
            "❌ This lookup session has expired.\n\n"
            "Please perform a new lookup."
        )
        return

    if not records:
        await query.edit_message_text(
            "❌ No lookup records available."
        )
        return

    total_pages = max(
        1,
        math.ceil(
            len(records) / RECORDS_PER_PAGE
        ),
    )

    if page < 0 or page >= total_pages:
        return

    text = build_page(
        records,
        number,
        page,
    )

    keyboard = pagination_keyboard(
        number,
        page,
        len(records),
    )

    await query.edit_message_text(
        text,
        reply_markup=keyboard,
    )


# ============================================================
# ADMIN MANAGEMENT
# ============================================================

def admin_keyboard():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📊 Stats",
                    callback_data="admin:stats",
                ),
                InlineKeyboardButton(
                    "🔎 QueryScope",
                    callback_data="admin:queries",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🗑️ Clear QueryScope",
                    callback_data="admin:clear_queries",
                ),
            ],
        ]
    )


async def bot_management(update: Update):

    user = update.effective_user

    if user.id != ADMIN_ID:
        await update.message.reply_text(
            "❌ Admin only."
        )
        return

    await update.message.reply_text(
        "⚙️ 𝗕𝗼𝘁 𝗠𝗮𝗻𝗮𝗴𝗲𝗺𝗲𝗻𝘁\n\n"
        "Select an option:",
        reply_markup=admin_keyboard(),
    )


# ============================================================
# ADMIN STATS
# ============================================================

async def admin_stats(query):

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "Admin only.",
            show_alert=True,
        )
        return

    users = get_users()
    verified = get_verified()

    if not verified:

        await query.edit_message_text(
            "📊 𝗕𝗢𝗧 𝗦𝗧𝗔𝗧𝗦\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 Total Users • {len(users)}\n"
            "✅ Verified Users • 0"
        )

        return

    lines = [
        "📊 𝗕𝗢𝗧 𝗦𝗧𝗔𝗧𝗦",
        "━━━━━━━━━━━━━━━━━━",
        f"👥 Total Users • {len(users)}",
        f"✅ Verified Users • {len(verified)}",
        "",
    ]

    for record in verified.values():

        username = record.get("username")

        if username:
            username_text = f"@{username}"
        else:
            username_text = "N/A"

        lines.extend(
            [
                f'👤 𝗡𝗮𝗺𝗲      • "{record.get("name") or "N/A"}"',
                f'🆔 𝗨𝘀𝗲𝗿 𝗜𝗗   • "{record.get("user_id")}"',
                f'🏷️ 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲  • "{username_text}"',
                f'☎️ 𝗖𝗼𝗻𝘁𝗮𝗰𝘁   • "{record.get("contact") or "N/A"}"',
                "━━━━━━━━━━━━━━━━━━",
            ]
        )

    text = "\n".join(lines)

    # Telegram message limit protection
    if len(text) > 3900:
        text = text[:3900] + "\n\n...output truncated."

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Back",
                        callback_data="admin:back",
                    )
                ]
            ]
        ),
    )


# ============================================================
# ADMIN QUERY SCOPE
# ============================================================

async def admin_queries(query):

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "Admin only.",
            show_alert=True,
        )
        return

    queries = get_queries()

    if not queries:

        await query.edit_message_text(
            "🔎 𝗤𝘂𝗲𝗿𝘆𝗦𝗰𝗼𝗽𝗲\n\n"
            "No queries recorded.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ Back",
                            callback_data="admin:back",
                        )
                    ]
                ]
            ),
        )

        return

    lines = [
        "🔎 𝗤𝗨𝗘𝗥𝗬𝗦𝗖𝗢𝗣𝗘",
        "━━━━━━━━━━━━━━━━━━",
    ]

    for index, item in enumerate(
        reversed(queries),
        start=1,
    ):

        number = str(item.get("number", ""))

        # Mask queried number except last 4 digits
        if len(number) > 4:
            display_number = (
                "*" * (len(number) - 4)
                + number[-4:]
            )
        else:
            display_number = "****"

        lines.extend(
            [
                f"#{index}",
                f"👤 {item.get('name') or 'N/A'}",
                f"🆔 {item.get('user_id')}",
                f"📞 {display_number}",
                "──────────────",
            ]
        )

    text = "\n".join(lines)

    if len(text) > 3900:
        text = text[:3900] + "\n\n...output truncated."

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Back",
                        callback_data="admin:back",
                    )
                ]
            ]
        ),
    )


# ============================================================
# CLEAR QUERIES
# ============================================================

async def clear_queries(query):

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "Admin only.",
            show_alert=True,
        )
        return

    save_queries([])

    await query.edit_message_text(
        "✅ QueryScope cleared.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Back",
                        callback_data="admin:back",
                    )
                ]
            ]
        ),
    )


# ============================================================
# ADMIN CALLBACK
# ============================================================

async def admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "Admin only.",
            show_alert=True,
        )

        return

    await query.answer()

    if query.data == "admin:stats":
        await admin_stats(query)

    elif query.data == "admin:queries":
        await admin_queries(query)

    elif query.data == "admin:clear_queries":
        await clear_queries(query)

    elif query.data == "admin:back":

        await query.edit_message_text(
            "⚙️ 𝗕𝗼𝘁 𝗠𝗮𝗻𝗮𝗴𝗲𝗺𝗲𝗻𝘁\n\n"
            "Select an option:",
            reply_markup=admin_keyboard(),
        )


# ============================================================
# GROUP PROTECTION
# ============================================================

async def group_protection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    change = update.my_chat_member

    if not change:
        return

    chat = change.chat
    new_member = change.new_chat_member

    if chat.type not in [
        ChatType.GROUP,
        ChatType.SUPERGROUP,
    ]:
        return

    status = new_member.status

    if status not in [
        "member",
        "administrator",
    ]:
        return

    approved = get_approved_groups()

    if chat.id in approved:
        return

    try:

        await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "❌ This bot is not approved for this group.\n\n"
                "The bot will leave now."
            ),
        )

        await context.bot.leave_chat(
            chat_id=chat.id
        )

        print(
            "Left unapproved group:",
            chat.id,
            chat.title,
        )

    except Exception as error:

        print(
            "GROUP PROTECTION ERROR:",
            repr(error),
        )


# ============================================================
# TEXT HANDLER
# ============================================================

async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user
    message = update.message

    if not user or not message:
        return

    if not is_verified(user.id):

        await message.reply_text(
            "🔐 Please verify first by sharing your own contact.",
            reply_markup=contact_keyboard(),
        )

        return

    text = message.text.strip()

    # Number lookup button
    if text == "🔎 Number Lookup":

        context.user_data["waiting_number"] = True

        await message.reply_text(
            "📞 Send 10-digit number:\n\n"
            "Example:\n"
            "9876543210"
        )

        return

    # My Contact
    if text == "👤 My Contact":

        await show_my_contact(update)

        return

    # Help
    if text == "❓ Help":

        await show_help(update)

        return

    # Management
    if text == "⚙️ Bot Management":

        await bot_management(update)

        return

    # Waiting for number
    if context.user_data.get(
        "waiting_number",
        False,
    ):

        context.user_data["waiting_number"] = False

        await process_number(
            update,
            context,
            text,
        )

        return

    await message.reply_text(
        "Please choose an option from the menu.",
        reply_markup=main_keyboard(user.id),
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    print(
        "BOT ERROR:",
        repr(context.error),
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 50)
    print("AKASH NUMBER LOOKUP BOT")
    print("Starting...")
    print("=" * 50)

    # Start Render health server
    health_thread = threading.Thread(
        target=run_health_server,
        daemon=True,
    )

    health_thread.start()

    # Telegram application
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # /start
    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    # Contact verification
    app.add_handler(
        MessageHandler(
            filters.CONTACT,
            handle_contact,
        )
    )

    # Lookup pagination
    app.add_handler(
        CallbackQueryHandler(
            pagination_callback,
            pattern=r"^lookup:",
        )
    )

    # Admin callbacks
    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^admin:",
        )
    )

    # Group protection
    app.add_handler(
        ChatMemberHandler(
            group_protection,
            ChatMemberHandler.MY_CHAT_MEMBER,
        )
    )

    # Text router
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text,
        )
    )

    # Errors
    app.add_error_handler(
        error_handler
    )

    print("Bot is running...")
    print("Health server: /health")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
