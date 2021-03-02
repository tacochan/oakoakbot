import glob
import io
import os

from PIL import Image

from oakoakbot.db import Pokemon
from oakoakbot.images import create_pokemon_image

BASE_PATH = "data/images/pokemon"
db_pokemon = Pokemon.select().where(Pokemon.enabled == 1).execute()


def preprocess_images(destination_folder):
    for pokemon in db_pokemon:
        # Get normal and shiny filenames
        f_normal = (
            f"{pokemon.number:04}_{pokemon.form:02}_{pokemon.region}_n_"
            f"{['n', 'm'][pokemon.mega]}_*.png"
        )
        f_shiny = (
            f"{pokemon.number:04}_{pokemon.form:02}_{pokemon.region}_s_"
            f"{['n', 'm'][pokemon.mega]}_*.png"
        )

        for find in glob.glob(os.path.join(BASE_PATH, f_normal)):
            image_byes = create_pokemon_image(find, pokemon.name, False)
            image = Image.open(io.BytesIO(image_byes))
            image.save(
                os.path.join(destination_folder, "images", os.path.basename(find))
            )

            image_byes = create_pokemon_image(find, pokemon.name, True)
            image = Image.open(io.BytesIO(image_byes))
            image.save(
                os.path.join(destination_folder, "silhouettes", os.path.basename(find))
            )

        for find in glob.glob(os.path.join(BASE_PATH, f_shiny)):
            image_byes = create_pokemon_image(find, pokemon.name, False)
            image = Image.open(io.BytesIO(image_byes))
            image.save(
                os.path.join(destination_folder, "images", os.path.basename(find))
            )
