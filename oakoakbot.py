import csv
import glob
import random
import time
import numpy as np
import sqlite3
import math
import os
import io

import asyncio
from PIL import Image, ImageDraw, ImageFont
from aiogram import Bot, Dispatcher, types

BASE_IMAGE = "data/images/misc/background_image.jpg"
POKEMON_LOGO = "data/images/misc/pokemon_logo.png"
QUESTION_MARK = "data/images/misc/question_mark.png"

# TODO: Pokemon chance is related to pokemon base stats + is_legendary
WILD_POKEMON_CHANCE = 0
SHADOW_OFFSET = (15, 12)
CONTOUR_OFFSET = (20, 15)
RGBA = {
    "blue": (22, 104, 151, 255),
    "darker_blue": (28, 69, 90, 180),
    "shadow": (72, 86, 112, 135),
    "yellow": (252, 202, 49, 255),
    "black": (0, 0, 0, 255),
}

t0 = time.time()
bot = Bot(token=os.environ["BOT_TOKEN"])
dispatcher = Dispatcher(bot=bot)
wild_pokemon = {}
images = os.listdir("data/images/pokemon")

with open("data/pokemon.csv") as f:
    pokemon_data = list(csv.DictReader(f))


# con = sqlite3.Connection("newdb.sqlite")
# cur = con.cursor()
# cur.execute('CREATE TABLE "pokemon" ("NUMBER" varchar(12), "two" varchar(12));')
#
# f = open("data/pokemon.csv")
# csv_reader = csv.reader(f, delimiter=";")
#
# cur.executemany("INSERT INTO pokemon VALUES (?, ?)", csv_reader)
# cur.close()
# con.commit()
# con.close()
# f.close()
# TODO: Filter pokemon with long names
# for pokemon in pokemon_data:
#     # if len(pokemon["name"]) > 11:
#     # print(pokemon)
#
#     if pokemon["pokedex_number"] == "876":
#         print(pokemon)

print(f"Setup finished in {time.time() - t0}s.")

# filename = images[random.randint(0, len(images) - 1)]
# image_path = os.path.join("data/images/pokemon", filename)
# image_path = (
#     filename
# ) = "data/images/pokemon/poke_capture_0025_000_md_n_00000000_f_n.png"


def silhouette_from_image(image, rgba):
    mask = (np.array(image)[..., 3] > 0).astype(np.uint8)
    return Image.fromarray(np.stack([colour * mask for colour in rgba], 2))


def paste_image_with_shadow(base_image, image, position):
    shadow = silhouette_from_image(image, RGBA["shadow"])
    blue_contour = silhouette_from_image(image, RGBA["darker_blue"])

    base_image.paste(shadow, position, shadow)
    base_image.paste(
        blue_contour,
        (position[0] + SHADOW_OFFSET[0], position[1] - SHADOW_OFFSET[1]),
        blue_contour,
    )
    base_image.paste(
        image, (position[0] + CONTOUR_OFFSET[0], position[1] - CONTOUR_OFFSET[1]), image
    )


def create_pokemon_image(pokemon_image, pokemon_name, is_silhouette):
    # Load base image
    base_image = Image.open(BASE_IMAGE).convert("RGB")

    # Create pokemon image or silhouette with shadows
    pokemon_image = Image.open(pokemon_image).convert("RGBA")
    pokemon_image = pokemon_image.crop(pokemon_image.getbbox())
    if is_silhouette:
        pokemon_image = silhouette_from_image(pokemon_image, RGBA["blue"])

    # Calculate pokemon position
    w_start = max(10, math.ceil(base_image.size[0] * 0.25 - pokemon_image.size[0] / 2))
    h_start = max(10, math.ceil(base_image.size[1] * 0.4 - pokemon_image.size[1] / 2))

    # Paste the pokemon image into the background
    paste_image_with_shadow(base_image, pokemon_image, (w_start, h_start))

    # Paste pokemon logo
    pokemon_logo = Image.open(POKEMON_LOGO).convert("RGBA")
    pokemon_logo.thumbnail(
        [math.ceil(dim * 0.5) for dim in pokemon_logo.size]
    )  # remove this
    pokemon_logo = pokemon_logo.crop(pokemon_logo.getbbox())
    paste_image_with_shadow(
        base_image,
        pokemon_logo,
        (math.ceil(base_image.size[0] * 0.45), math.ceil(base_image.size[1] * 0.6)),
    )

    if is_silhouette:
        # Paste pokemon logo
        question_mark = Image.open(QUESTION_MARK).convert("RGBA")
        question_mark.thumbnail(
            [math.ceil(dim * 0.75) for dim in question_mark.size]
        )  # remove this
        question_mark = question_mark.crop(question_mark.getbbox())
        paste_image_with_shadow(
            base_image,
            question_mark,
            (
                math.ceil(base_image.size[0] * 0.6),
                math.ceil(base_image.size[1] * 0.15),
            ),
        )
    else:
        # Paste pokemon font
        text_image = Image.new("RGBA", (800, 300), (255, 255, 255, 0))
        contour_image = Image.new("RGBA", (800, 300), (255, 255, 255, 0))

        font = ImageFont.truetype("data/fonts/Playhouse Medium.ttf", 100)
        text_pos = (400, 150)

        draw = ImageDraw.Draw(text_image)
        draw.text(
            text_pos,
            pokemon_name.upper(),
            fill=RGBA["blue"],
            font=font,
            anchor="mm",
            stroke_width=7,
            stroke_fill=RGBA["black"],
        )

        draw = ImageDraw.Draw(contour_image)
        draw.text(
            text_pos,
            pokemon_name.upper(),
            fill=(0, 0, 0, 0),
            font=font,
            anchor="mm",
            stroke_width=5,
            stroke_fill=RGBA["yellow"],
        )
        # text_image.show()
        text_image = Image.alpha_composite(text_image, contour_image)
        text_image.crop(text_image.getbbox())
        paste_image_with_shadow(
            base_image,
            text_image,
            (
                math.ceil(base_image.size[0] * 0.71 - text_image.size[0] * 0.5),
                math.ceil(base_image.size[1] * 0.33 - text_image.size[1] * 0.5),
            ),
        )

    # Resize the image to increase response time (make this parameterizable)
    base_image.thumbnail([math.ceil(dim * 0.6) for dim in base_image.size])

    # Save it to bytes buffer
    with io.BytesIO() as output:
        base_image.save(output, format="GIF")
        bytes_image = output.getvalue()

    return bytes_image


# create_pokemon_image(image_path, False)
# exit()


@dispatcher.message_handler(
    chat_type=[types.ChatType.PRIVATE],
    commands=["start", "restart", "help"],
)
async def start_handler(event: types.Message):
    await event.answer("Bot in development.")
    return
    await event.answer(
        f"Hello, {event.from_user.get_mention(as_html=True)} 👋!\n\n"
        f"My name is Samuel Oak. I can be added to any group, and if I'm given the "
        f"right permissions, I'll notify you whenever a wild pokemon appears.\n\n"
        f"You can then catch wild pokemon by using the /catch command followed "
        f"by the name of the pokemon you want to catch.\n\n"
        f"You can check your team at any time using the /showteam command.",
        parse_mode=types.ParseMode.HTML,
    )


@dispatcher.message_handler(
    chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP], commands=["catch"]
)
async def capture_handler(event: types.Message):
    pokemon_to_capture = event.text.replace("/catch", "").strip().lower()
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
        print(f"{pokemon['NAME']} released into the wild")


async def main():
    try:
        print("Waiting for messages...")
        await dispatcher.start_polling()
    finally:
        await bot.close()


asyncio.run(main())
