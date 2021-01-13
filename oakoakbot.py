import asyncio
import csv
import glob
import os
import random
import time

from aiogram import Bot, Dispatcher, types

from oakoakbot.db import OakDB
from oakoakbot.logger import get_logger
from oakoakbot.images import create_pokemon_image

logger = get_logger()

t0 = time.time()
bot = Bot(token=os.environ["BOT_TOKEN"])
dispatcher = Dispatcher(bot=bot)
oak_db = OakDB()

WILD_POKEMON_CHANCE = 0

wild_pokemon = {}
images = os.listdir("data/images/pokemon")

with open("data/pokemon.csv") as f:
    pokemon_data = list(csv.DictReader(f))


logger.info(f"Initial setup finished in {time.time() - t0}s.")


@dispatcher.message_handler(
    chat_type=[types.ChatType.PRIVATE],
    commands=["start", "restart", "help"],
)
async def start_handler(event: types.Message):
    await event.answer("Bot in development.")
    return
    await event.answer(
        f"Hello, {event.from_user.get_mention(as_html=True)} 👋!\n\n"
        f"I'm Professor Oak. I can be added to any group, and if I'm given the "
        f"right permissions, I'll notify you whenever a wild Pokemon appears.\n\n"
        f"You can then catch wild Pokemon by using the /catch command followed "
        f"by the name of the Pokemon you want to catch.\n\n"
        f"You can check your team at any time using the /showteam command. \n\n",
        parse_mode=types.ParseMode.HTML,
    )


@dispatcher.message_handler(
    chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP],
    commands=["help"],
)
async def help_handler(event: types.Message):
    await event.answer(
        f"Pokemon will appear randomly\. Catch them to add them to your team\!"
        f"\n\n"
        f"/catch <pokemon name\> \- Catch a wild Pokemon\. Only Pokemon notified "
        f"by Professor Oak can be caught\!\."
        f"\n"
        f"/setgens <gens\> \- Specify which generation of Pokemon will appear on "
        f"this group\. Generations must be comma separated numbers on the range "
        f"\[1,8\]\."
        f"\n"
        f"/setrate <rate\> \- Specify the rate at which wild Pokemon will appear on "
        f"this group\. <rate\> must be a float between 0 and 1\. Each message will "
        f"have a chance of <rate\> to spawn a wild Pokemon\."
        f"\n"
        f"/showteam \- See the Pokemon you've captured on this group\."
        f"\n\n\n"
        f"Bugs and suggestions can be reported on oakoakbot's "
        f"[GitHub page](https://github.com/tacochan/oakoakbot)\.",
        parse_mode=types.ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )


@dispatcher.message_handler(
    chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP], commands=["catch"]
)
async def capture_handler(event: types.Message):
    pokemon_to_capture = event.text.replace("/catch", "").replace("@oakoakbot", "")
    pokemon_to_capture = pokemon_to_capture.strip().lower()
    if pokemon_to_capture in wild_pokemon:
        caught_pokemon = wild_pokemon.pop(pokemon_to_capture)
        image_path = glob.glob(
            f"data/images/pokemon/poke_capture_{int(caught_pokemon['NUMBER']):04}*_f_n.png"
        )[0]
        image = create_pokemon_image(image_path, pokemon_to_capture, False)
        await event.answer_photo(
            image,
            f"All right! {pokemon_to_capture} was caught!",
        )
    elif pokemon_to_capture in ["oak", "professor oak", "samuel oak"]:
        await event.answer(
            f"Hey! I'm not yours to catch!",
        )
    elif pokemon_to_capture:
        await event.answer(
            f"Hm no, I haven't seen any wild {pokemon_to_capture}",
        )
    else:
        await event.answer(
            f"You must tell me which pokemon you want to capture",
        )


@dispatcher.message_handler(
    chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP],
    commands=["setrate"],
)
async def set_rate_handler(event: types.Message):
    new_rate = event.text.replace("/setrate", "").replace("@oakoakbot", "")
    new_rate = new_rate.strip().lower()

    if not new_rate:
        await event.answer(
            f"You must specify a <rate\> parameter\. Example: `/setrate 0\.01`",
            parse_mode=types.ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
        )
        return

    try:
        new_rate = float(new_rate)
        if new_rate < 0 or new_rate > 1:
            raise ValueError
        oak_db.update_group_pokemon_rate(event.chat.id, new_rate)
        logger.info(f"Rate for group {event.chat.id} set to {new_rate}")

        await event.answer(
            f"Pokemon rate was successfully updated",
            parse_mode=types.ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
        )

    except ValueError:
        await event.answer(
            f"<rate\> parameter must be a number between 0 and 1\. "
            f"Example: `/setrate 0\.01`",
            parse_mode=types.ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
        )


@dispatcher.message_handler(
    chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP],
    commands=["setgens"],
)
async def set_rate_handler(event: types.Message):
    gens = event.text.replace("/setgens", "").replace("@oakoakbot", "")
    gens = gens.strip().lower()

    if not gens:
        await event.answer(
            f"You must specify a <gens\> parameter\. Example: `/setgens 1,2,3`",
            parse_mode=types.ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
        )
        return

    try:
        gen_list = [int(gen) for gen in gens.split(",")]
        oak_db.update_group_generations(event.chat.id, gen_list)

        await event.answer(
            f"From now on, only Pokemon of generations {gens} will appear.",
            parse_mode=types.ParseMode.HTML,
            disable_web_page_preview=True,
        )

    except ValueError:
        await event.answer(
            f"<gens\> parameter must be a list of numbers on the range \[1,8\] "
            f"separated by commas\. Example: 1,2,3",
            parse_mode=types.ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
        )


@dispatcher.message_handler(
    chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP], commands=["showteam"]
)
async def capture_handler(event: types.Message):
    return


@dispatcher.message_handler(
    chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP],
)
async def message_handler(event: types.Message):
    r = random.random()
    if r > WILD_POKEMON_CHANCE and not len(wild_pokemon):
        pokemon = pokemon_data[random.randint(0, 386)]  # len(pokemon_data) - 1)]
        wild_pokemon[pokemon["NAME"].split()[0].lower()] = pokemon
        image_path = glob.glob(
            f"data/images/pokemon/poke_capture_{int(pokemon['NUMBER']):04}*_f_n.png"
        )[0]
        image = create_pokemon_image(image_path, pokemon["NAME"], True)
        await event.answer_photo(
            image,
            f"A wild pokemon appeared!",
        )
        logger.info(f"{pokemon['NAME']} released on group {event.chat.id}")


async def main():
    try:
        logger.info("Waiting for messages...")
        await dispatcher.start_polling()
    finally:
        await bot.close()


asyncio.run(main())
