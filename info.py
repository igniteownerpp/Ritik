import shelve
import time
import requests
from telegram import Update, User
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

BOT_TOKEN = "8478339174:AAEnVV2CsCkWMyRpdMiYamIOJnYWcrLqZoA"
ADMIN_IDS = {7629111869,6437994839}
CHANNEL_LINK = "https://t.me/+T_rmQaz1xCM2ODZl"

COIN_PACKS = [
    (100, 20),
    (200, 40),
    (300, 60),
    (400, 80),
    (500, 100),
]

USER_DB = "user_db"
GROUP_DB = "group_db"
DEFAULT_MIN_USERS = 80
COIN_RESET_INTERVAL = 3 * 24 * 60 * 60  # 3 days in seconds


# User helper functions
def get_user_info(user_id: int):
    with shelve.open(USER_DB) as db:
        user = db.get(str(user_id), {
            "coins": 100,
            "last_reset": time.time(),
            "username": "",
            "fname": "",
            "lname": ""
        })
        if time.time() - user.get("last_reset", 0) > COIN_RESET_INTERVAL:
            user["coins"] = 100
            user["last_reset"] = time.time()
            db[str(user_id)] = user
        return user


def update_user(user_id: int, data: dict):
    with shelve.open(USER_DB) as db:
        user = db.get(str(user_id), {})
        user.update(data)
        db[str(user_id)] = user


def add_coins(user_id: int, amount: int):
    user = get_user_info(user_id)
    user["coins"] += amount
    update_user(user_id, user)


def set_username_and_names(user_id: int, user: User):
    data = {
        "username": user.username or "",
        "fname": user.first_name or "",
        "lname": user.last_name or ""
    }
    update_user(user_id, data)


def get_all_user_ids():
    with shelve.open(USER_DB) as db:
        return list(db.keys())


# Group helper functions
def get_min_users(chat_id):
    with shelve.open(GROUP_DB) as db:
        return db.get(str(chat_id), DEFAULT_MIN_USERS)


def set_min_users(chat_id, min_users):
    with shelve.open(GROUP_DB) as db:
        db[str(chat_id)] = min_users


async def check_min_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    if chat.type in ["group", "supergroup"]:
        min_users = get_min_users(chat.id)
        try:
            member_count = await context.bot.get_chat_member_count(chat.id)
            if member_count < min_users:
                await update.message.reply_text(
                    f"Requirement not met: This group has {member_count} members.\nMinimum needed: {min_users}."
                )
                return False
        except Exception:
            await update.message.reply_text("Unable to verify group member count.")
            return False
    return True


# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_min_users(update, context):
        return
    set_username_and_names(update.effective_user.id, update.effective_user)
    await update.message.reply_text("Welcome! Type /help for commands.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_min_users(update, context):
        return
    msg = f"""This bot is made by @ritikxyz099 X @ParadoxIsBack.
Join channel: {CHANNEL_LINK}
Only Indian numbers accepted.

/help - Show commands
/num - Enter number
/info - User info & coins
/coin - Price packs

Admin commands:
/addmin <number> - Set min group members
/addcoins <user_id> <amount>
/msgall <msg>
/msgid <user_id> <msg>
/boton - Activate bot
/botoff - Deactivate bot
/userinfo <user_id>
"""
    await update.message.reply_text(msg)


async def num_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_min_users(update, context):
        return
    await update.message.reply_text("Please send a 10-digit Indian mobile number.")


async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_min_users(update, context):
        return
    set_username_and_names(update.effective_user.id, update.effective_user)
    user = get_user_info(update.effective_user.id)
    await update.message.reply_text(f"{user['fname']} {user['lname']}\nCoins: {user['coins']}")


async def coin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_min_users(update, context):
        return
    lines = ["Coin Packs:"]
    for coins, price in COIN_PACKS:
        lines.append(f"{coins} coins – ₹{price}")
    await update.message.reply_text("\n".join(lines))


async def admincmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    msg = (
        "/addcoins <user_id> <amount>\n"
        "/msgall <msg>\n"
        "/msgid <user_id> <msg>\n"
        "/addmin <number> - Set min group members\n"
        "/boton - Activate bot\n"
        "/botoff - Deactivate bot\n"
        "/userinfo <user_id>"
    )
    await update.message.reply_text(msg)


async def addcoins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(context.args[0])
        amount = int(context.args[1])
        add_coins(uid, amount)
        await update.message.reply_text(f"Added {amount} coins to {uid}.")
    except:
        await update.message.reply_text("Usage: /addcoins <user_id> <amount>")


async def msgall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    msg = " ".join(context.args)
    for uid in get_all_user_ids():
        await context.bot.send_message(int(uid), msg)
    await update.message.reply_text("Sent to all users.")


async def msgid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(context.args[0])
        msg = " ".join(context.args[1:])
        await context.bot.send_message(uid, msg)
        await update.message.reply_text(f"Sent to {uid}.")
    except:
        await update.message.reply_text("Usage: /msgid <user_id> <msg>")


async def boton_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    for uid in get_all_user_ids():
        await context.bot.send_message(int(uid), "Bot is now active.")
    await update.message.reply_text("All users notified.")


async def botoff_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    for uid in get_all_user_ids():
        if int(uid) not in ADMIN_IDS:
            await context.bot.send_message(int(uid), "Bot is now off for non-admins.")
    await update.message.reply_text("Deactivated for non-admins.")


async def userinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_min_users(update, context):
        return
    try:
        uid = int(context.args[0])
        info = get_user_info(uid)
        await update.message.reply_text(
            f"User ID: {uid}\nName: {info['fname']} {info['lname']}\nCoins: {info['coins']}"
        )
    except:
        await update.message.reply_text("Usage: /userinfo <user_id>")


async def addmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    chat = update.effective_chat
    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Use /addmin inside a group.")
        return
    try:
        min_users = int(context.args[0])
        set_min_users(chat.id, min_users)
        await update.message.reply_text(f"Minimum users for this group set to {min_users}.")
    except:
        await update.message.reply_text("Usage: /addmin <number>")


async def echo_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_min_users(update, context):
        return
    text = update.message.text.strip()
    if text.isdigit() and len(text) == 10 and text[0] in "6789":
        user = get_user_info(update.effective_user.id)
        if user["coins"] < 10:
            await update.message.reply_text("Not enough coins! Use /coin.")
            return
        api_url = f"https://osient.vercel.app/v1/mobile?num={text}"
        r = requests.get(api_url)
        info = r.text
        user["coins"] -= 10
        update_user(update.effective_user.id, user)
        await update.message.reply_text(f"Info:\n{info}\nCoins: {user['coins']}")
    else:
        await update.message.reply_text("Send a valid 10-digit Indian mobile number.")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("num", num_command))
    app.add_handler(CommandHandler("info", info_command))
    app.add_handler(CommandHandler("coin", coin_command))
    app.add_handler(CommandHandler("admincmd", admincmd))
    app.add_handler(CommandHandler("addcoins", addcoins_command))
    app.add_handler(CommandHandler("msgall", msgall_command))
    app.add_handler(CommandHandler("msgid", msgid_command))
    app.add_handler(CommandHandler("boton", boton_command))
    app.add_handler(CommandHandler("botoff", botoff_command))
    app.add_handler(CommandHandler("userinfo", userinfo_command))
    app.add_handler(CommandHandler("addmin", addmin_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_mobile))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
