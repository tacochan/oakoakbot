import asyncio
import argparse
import datetime
import os
import random
import string
import time

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.middlewares import BaseMiddleware

from oakoakbot.db import (
    Pokemon,
    CaughtPokemon,
    GroupsConfiguration,
    PokemonNatures,
    WildEncounter,
)
from oakoakbot.images import create_pokemon_image
from oakoakbot.logger import get_logger

logger = get_logger()

bot = Bot(token=os.environ["BOT_TOKEN"])
dispatcher = Dispatcher(bot=bot)

POKEMON_TIMEOUT = 120
SHINY_CHANCE = 1 / 10000
RARITY_TIERS = {
    "ultra-rare": 0.025,
    "rare": 0.15,  # 0.125
    "common": 0.50,  # 0.35
    "ultra-common": 1,  # 0.50
}

wild_encounters = {}


def pokemon_names_are_equivalent(pokemon_guess: str, wild_encounter: WildEncounter):
    """Compare if two strings containing pokemon names are equal enough for the pokemon
    to be considered caught
    """
    pokemon_guess = pokemon_guess.lower()
    wild_pokemon_name = wild_encounter.pokemon.name.lower()

    # Allow both adding and not adding the region name
    for region in ["alolan", "galarian"]:
        if wild_encounter.pokemon.region == region:
            if (
                pokemon_guess.startswith(region)
                or pokemon_guess.startswith(region[:-1])
                or pokemon_guess.endswith(region)
                or pokemon_guess.endswith(region[:-1])
            ):
                pokemon_guess = pokemon_guess.replace(region, "")
                pokemon_guess = pokemon_guess.replace(region[:-1], "")

    # Allow both adding and not adding gender
    if wild_pokemon_name.endswith(" m"):
        pokemon_guess = pokemon_guess.replace(" male", "").replace("male ", "")
        pokemon_guess = pokemon_guess.replace(" m", "") + " m"
    if wild_pokemon_name.endswith(" f"):
        pokemon_guess = pokemon_guess.replace(" female", "").replace(" female", "")
        pokemon_guess = pokemon_guess.replace(" f", "") + " f"

    # Remove spaces and punctuations from both strings
    trans_table = str.maketrans("", "", string.punctuation + " ")
    pokemon_guess = pokemon_guess.translate(trans_table)
    wild_pokemon_name = wild_pokemon_name.translate(trans_table)

    return pokemon_guess == wild_pokemon_name


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
        f"/showteam \- See the Pokemon you've caught on this group\."
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
            f"From now on, only Pokemon of generation"
            f"{'s' if len(generations) > 1 else ''} "
            f"{','.join(str(gen) for gen in generations)} will appear.",
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

    pokemon = await CaughtPokemon.get_caught_pokemon(event.from_user.id, event.chat.id)
    if not len(pokemon):
        answer = f"You still haven't caught any Pokemon!"
    else:
        answer = f"{event.from_user.get_mention(as_html=True)}'s caught Pokemon:\n"
        for p in pokemon[50]:
            answer += f"{p.team_pokemon_id + 1}. {p.pokemon.name}\n"
        if len(pokemon) > 50:
            answer = (
                f"\nOnly your first 50 Pokemon can be shown, I'll eventually "
                f"find a way to fix that."
            )

    await event.answer(
        answer,
        parse_mode=types.ParseMode.HTML,
        disable_web_page_preview=True,
    )


@dispatcher.message_handler(
    chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP], commands=["catch"]
)
async def catch_handler(event: types.Message):
    pokemon_guess = event.get_args()
    wild_encounter = wild_encounters.get(event.chat.id)

    if wild_encounter and pokemon_names_are_equivalent(pokemon_guess, wild_encounter):
        caught_pokemon = wild_encounters.pop(event.chat.id)
        image = await create_pokemon_image(
            caught_pokemon.sprite_filename, wild_encounter.pokemon.name, False
        )
        await CaughtPokemon.catch_pokemon(
            caught_pokemon, event.from_user.id, event.chat.id
        )
        if caught_pokemon.shiny:
            await event.answer_photo(
                image,
                f"AWESOME! {event.from_user.get_mention(as_html=True)} caught a "
                f"<b>shiny {wild_encounter.pokemon.name}</b>!",
                parse_mode=types.ParseMode.HTML,
            )

        else:
            await event.answer_photo(
                image,
                f"Congratulations {event.from_user.get_mention(as_html=True)}! "
                f"{wild_encounter.pokemon.name} was caught!",
                parse_mode=types.ParseMode.HTML,
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
            f"You must tell me which pokemon you want to catch",
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
    elif (r := random.random()) < GroupsConfiguration.get_pokemon_rate(event.chat.id):
        shiny = r < SHINY_CHANCE
        rarity = next(tier for tier, chance in RARITY_TIERS.items() if r < chance)
        generations = GroupsConfiguration.get_generations(event.chat.id)
        wild_encounter = Pokemon.get_random_encounter(generations, rarity, shiny)
        wild_encounters[event.chat.id] = wild_encounter
        image = await create_pokemon_image(
            wild_encounter.sprite_filename, wild_encounter.pokemon.name, True
        )
        await event.answer_photo(
            image,
            f"A wild pokemon appeared!",
        )
        logger.info(f"{wild_encounter.pokemon.name} released on group {event.chat.id}")


async def start():
    try:
        logger.info("Waiting for messages...")
        dispatcher.middleware.setup(GroupCheck())
        await dispatcher.start_polling()
    finally:
        await bot.close()


async def populate_database(entries):
    pokemon = []
    tier = list(RARITY_TIERS)[random.randint(0, 3)]
    wild_encounter = Pokemon.get_random_encounter(list(range(1, 9)), tier)
    date_now = datetime.datetime.now()
    for i in range(entries):
        pokemon.append(
            {
                "team": 1,
                "team_pokemon_id": 1,
                "pokemon": wild_encounter.pokemon.id,
                "catch_date": date_now,
                "shiny": wild_encounter.shiny,
                "gender": wild_encounter.gender,
                "ability": wild_encounter.ability,
                "nature": wild_encounter.nature,
                "hp_iv": 1,
                "attack_iv": 1,
                "defense_iv": 1,
                "special_attack_iv": 1,
                "special_defense_iv": 1,
                "speed_iv": 1,
            }
        )
    insert_t0 = time.time()
    CaughtPokemon.insert_many(pokemon).execute()
    logger.info(f"{entries} Pokemon inserted in {time.time() - insert_t0}s")


async def check_performance(loops):
    total_image_time = 0

    for i in range(loops):
        wild_encounter = Pokemon.get_random_encounter(-1001237373620)
        t_image = time.time()
        await create_pokemon_image(
            wild_encounter.sprite_filename, wild_encounter.pokemon.name, True
        )
        total_image_time += time.time() - t_image

    logger.info(
        f"Stress test finished. {loops} images processed in {total_image_time:03}s\n"
        f" with an average of {total_image_time/loops:04}s per image"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Oakoakbot's command line.")
    parser.add_argument(
        "action",
        choices=[
            "start",
            "init-images",
            "init-db",
            "validate-data",
            "check-performance",
            "populate_database",
        ],
        type=str,
    )
    args = parser.parse_args()

    if args.action == "start":
        asyncio.run(start())
    elif args.action == "init-db":
        query_t0 = time.time()
        Pokemon.init_table_from_csv("data/pokemon.csv")
        PokemonNatures.init_table_from_csv("data/natures.csv")
        logger.info(f"DB initialization finished in {time.time() - query_t0:02}s.")
    elif args.action == "validate-data":
        from scripts.data_validator import validate_data

        validate_data()
    elif args.action == "check-performance":
        asyncio.run(check_performance(100))
    elif args.action == "init-images":
        from scripts.image_preprocess import preprocess_images

        preprocess_images()
