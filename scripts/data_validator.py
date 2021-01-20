from oakoakbot.db import Pokemon
import glob
import os

BASE_PATH = "data/images/pokemon"


def validate_data():
    im_pokemon = glob.glob(os.path.join(BASE_PATH, "*"))
    db_pokemon = Pokemon.select().where(Pokemon.enabled == 1).execute()

    # First, check that all Pokemon on the database have all images
    pokemon_without_image = []
    for pokemon in db_pokemon:
        f_normal = (
            f"{pokemon.number:04}_{pokemon.form:02}_{pokemon.region}_n_"
            f"{['n','m'][pokemon.mega]}_*.png"
        )
        f_shiny = (
            f"{pokemon.number:04}_{pokemon.form:02}_{pokemon.region}_s_"
            f"{['n','m'][pokemon.mega]}_*.png"
        )
        finds_normal = glob.glob(os.path.join("data/images/pokemon", f_normal))
        finds_shiny = glob.glob(os.path.join("data/images/pokemon", f_shiny))
        if len(finds_normal) != len(finds_shiny):
            pokemon_without_image.append(pokemon)
        elif len(finds_normal) == 0:
            pokemon_without_image.append(pokemon)
        elif len(finds_normal) == 2:
            for fn, fs in zip(finds_normal, finds_shiny):
                if "_md" not in fn and "_fd" not in fn:
                    pokemon_without_image.append(pokemon)
                if "_md" not in fs and "_fd" not in fs:
                    pokemon_without_image.append(pokemon)

    # Then, check that all images are correctly registered in the db.
    images_without_pokemon = []
    for pokemon in im_pokemon:
        att = pokemon.split("/")[-1].split("_")
        num = int(att[0])
        form = int(att[1])
        region = att[2]
        mega = att[4] == "m"

        a = list(
            Pokemon.select().where(
                (
                    (Pokemon.number == num)
                    & (Pokemon.form == form)
                    & (Pokemon.region == region)
                    & (Pokemon.mega == mega)
                )
            )
        )
        if len(a) == 0:
            images_without_pokemon.append((num, form))

    print(pokemon_without_image)
    print(images_without_pokemon)
