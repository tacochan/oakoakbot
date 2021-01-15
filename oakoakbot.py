import asyncio
import csv
import os
import random
import time
import string

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.middlewares import BaseMiddleware

from oakoakbot.db import Pokemon, CaughtPokemon, GroupsConfiguration, Teams
from oakoakbot.logger import get_logger
from oakoakbot.images import create_pokemon_image


logger = get_logger()

t0 = time.time()
bot = Bot(token=os.environ["BOT_TOKEN"])
dispatcher = Dispatcher(bot=bot)

POKEMON_TIMEOUT = 16

wild_encounters = {}
images = os.listdir("data/images/pokemon")

with open("data/pokemon.csv") as f:
    pokemon_data = list(csv.DictReader(f))


logger.info(f"Initial setup finished in {time.time() - t0}s.")

trans_table = str.maketrans("", "", string.punctuation + " ")


def compare_pokemon(pokemon1: str, pokemon2: str):
    """Compare if two strings containing pokemon names are equal enough for the pokemon
    to be considered caught
    """
    pokemon1 = pokemon1.lower().translate(trans_table)
    pokemon2 = pokemon2.lower().translate(trans_table)
    return pokemon1 == pokemon2


class GroupCheck(BaseMiddleware):
    def __init__(self) -> None:
        self.groups = GroupsConfiguration.get_groups()
        super(GroupCheck, self).__init__()

    async def on_process_message(self, event, _):
        """Manage the current list of registered groups. Called on every message before
        dispatching them to the handlers.
        """
        if event.chat.id not in self.groups:
            GroupsConfiguration.add_group(event.chat.id)
            self.groups = GroupsConfiguration.get_groups()


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
    chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP],
    commands=["setrate"],
)
async def set_rate_handler(event: types.Message):
    new_rate = event.get_args()

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
        GroupsConfiguration.set_pokemon_rate(event.chat.id, new_rate)
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
async def set_gens_handler(event: types.Message):
    gens = event.get_args()

    if not gens:
        await event.answer(
            f"You must specify a <gens\> parameter\. Example: `/setgens 1,2,3`",
            parse_mode=types.ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
        )
        return

    try:
        generations = [int(gen) for gen in gens.split(",")]
        if any([gen > 8 or gen < 0 for gen in generations]):
            raise ValueError

        GroupsConfiguration.set_generations(event.chat.id, generations)

        await event.answer(
            f"From now on, only Pokemon of generation(s) {gens} will appear.",
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
async def show_team_handler(event: types.Message):
    return


@dispatcher.message_handler(
    chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP], commands=["catch"]
)
async def capture_handler(event: types.Message):
    pokemon_guess = event.get_args()
    wild_encounter = wild_encounters.get(event.chat.id)

    if wild_encounter and compare_pokemon(pokemon_guess, wild_encounter.pokemon.name):
        caught_pokemon = wild_encounters.pop(event.chat.id)
        image = await create_pokemon_image(
            caught_pokemon.sprite_filename, wild_encounter.pokemon.name, False
        )
        if caught_pokemon.shiny:
            await event.answer_photo(
                image,
                f"AWESOME\! {event.from_user.get_mention()} caught a "
                f"*shiny {wild_encounter.pokemon.name}*\!",
                parse_mode=types.ParseMode.MARKDOWN_V2,
            )

        else:
            await event.answer_photo(
                image,
                f"Congratulations {event.from_user.get_mention()}\! "
                f"{wild_encounter.pokemon.name} was caught\!",
                parse_mode=types.ParseMode.MARKDOWN_V2,
            )
    elif pokemon_guess in ["oak", "professor oak", "samuel oak"]:
        await event.answer(
            f"Hey! I'm not yours to catch!",
        )
    elif pokemon_guess:
        await event.answer(
            f"Hm no, I haven't seen any wild {pokemon_guess}",
        )
    else:
        await event.answer(
            f"You must tell me which pokemon you want to capture",
        )


@dispatcher.message_handler(
    chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP],
)
async def message_handler(event: types.Message):
    """Handler called every time a message is sent to a group and it's not a command.
    It rolls a random and if it's under the group's pokemon rate it spawns a pokemon.
    """
    if event.chat.id in wild_encounters:
        if time.time() - wild_encounters[event.chat.id].release_time > POKEMON_TIMEOUT:
            wild_encounters.pop(event.chat.id)
            await event.answer(
                f"Oh no! the wild pokemon fled!",
            )

    elif random.random() < GroupsConfiguration.get_pokemon_rate(event.chat.id):
        wild_encounter = Pokemon.get_random_encounter(event.chat.id)
        wild_encounters[event.chat.id] = wild_encounter
        image = await create_pokemon_image(
            wild_encounter.sprite_filename, wild_encounter.pokemon.name, True
        )
        await event.answer_photo(
            image,
            f"A wild pokemon appeared!",
        )
        logger.info(f"{wild_encounter.pokemon.name} released on group {event.chat.id}")


async def main():
    try:
        logger.info("Waiting for messages...")
        dispatcher.middleware.setup(GroupCheck())
        await dispatcher.start_polling()
    finally:
        await bot.close()


asyncio.run(main())
